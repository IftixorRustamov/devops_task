import json
import unittest

import _paths  # noqa: F401
from crystal_common.bus import InMemoryBus, topic_matches
from crystal_common.config import mask_url
from crystal_common.db import Database, Session
from crystal_common.errors import UpstreamError
from crystal_common.events import (
    INBOX_DDL, OUTBOX_DDL, OutboxRelay, handle_once, new_event, pending_count, record_event,
)
from crystal_common.http import CircuitBreaker, ServiceClient
from helpers import TempDatabases


class TopicTest(unittest.TestCase):
    def test_patterns(self):
        self.assertTrue(topic_matches("order.*", "order.created"))
        self.assertFalse(topic_matches("order.*", "order.status.changed"))
        self.assertTrue(topic_matches("order.#", "order.status.changed"))
        self.assertTrue(topic_matches("#", "courier.assigned"))
        self.assertFalse(topic_matches("courier.assigned", "order.created"))


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.dbs = TempDatabases()
        self.addCleanup(self.dbs.cleanup)
        self.db = self.dbs.create("common", "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")

    def test_rejects_unknown_and_memory_urls(self):
        with self.assertRaises(ValueError):
            Database("mysql://x")
        with self.assertRaises(ValueError):
            Database("sqlite:///:memory:")

    def test_postgres_placeholders(self):
        class Recorder:
            def execute(self, sql, params):
                self.sql, self.params = sql, params

        recorder = Recorder()
        Session(recorder, "postgres").execute("SELECT ? , ?", [1, 2])
        self.assertEqual(recorder.sql, "SELECT %s , %s")
        self.assertEqual(recorder.params, (1, 2))
        self.assertEqual(Database("postgresql://u:p@h/db").for_update, " FOR UPDATE")
        self.assertEqual(self.db.for_update, "")

    def test_rollback_on_error(self):
        with self.assertRaises(RuntimeError):
            with self.db.session(write=True) as session:
                session.execute("INSERT INTO items (name) VALUES (?)", ("a",))
                raise RuntimeError("stop")
        with self.db.session() as session:
            self.assertEqual(session.one("SELECT COUNT(*) FROM items")[0], 0)
        self.assertTrue(self.db.ping())

    def test_migrations_run_once_in_order(self):
        migrations = [
            (2, {"sqlite": ["ALTER TABLE items ADD COLUMN price INTEGER"]}),
            (3, {"sqlite": ["CREATE INDEX IF NOT EXISTS items_price ON items (price)"]}),
        ]
        self.db.migrate(migrations)
        self.db.migrate(migrations)  # ikkinchi marta — hech narsa qilmaydi (aks holda ALTER xato beradi)
        with self.db.session() as session:
            self.assertEqual([r[0] for r in session.all("SELECT version FROM schema_migrations ORDER BY version")], [2, 3])
            session.execute("SELECT price FROM items")

    def test_mask_url_hides_password(self):
        self.assertEqual(mask_url("postgresql://order:secret@order-db:5432/order"),
                         "postgresql://order:***@order-db:5432/order")
        self.assertEqual(mask_url(""), "")


class OutboxInboxTest(unittest.TestCase):
    def setUp(self):
        self.dbs = TempDatabases()
        self.addCleanup(self.dbs.cleanup)
        self.producer = self.dbs.create("producer", OUTBOX_DDL)
        self.consumer = self.dbs.create("consumer", INBOX_DDL + "CREATE TABLE seen (id TEXT)")
        self.bus = InMemoryBus()

    def test_event_is_published_once_after_commit(self):
        with self.producer.session(write=True) as session:
            record_event(session, new_event("order.created", {"code": "CRY-1"}, "test"))
        self.assertEqual(pending_count(self.producer), 1)
        relay = OutboxRelay(self.producer, self.bus)
        self.assertEqual(relay.run_once(), 1)
        self.assertEqual(relay.run_once(), 0)
        self.assertEqual(pending_count(self.producer), 0)
        self.assertEqual(self.bus.published[0]["payload"], {"code": "CRY-1"})

    def test_rolled_back_event_is_never_published(self):
        with self.assertRaises(RuntimeError):
            with self.producer.session(write=True) as session:
                record_event(session, new_event("order.created", {}, "test"))
                raise RuntimeError("biznes xato")
        self.assertEqual(OutboxRelay(self.producer, self.bus).run_once(), 0)

    def test_failed_publish_keeps_event_pending(self):
        class BrokenBus:
            def publish(self, _event):
                raise ConnectionError("broker ishlamayapti")

        with self.producer.session(write=True) as session:
            record_event(session, new_event("order.created", {}, "test"))
        with self.assertRaises(ConnectionError):
            OutboxRelay(self.producer, BrokenBus()).run_once()
        self.assertEqual(pending_count(self.producer), 1)

    def test_duplicate_event_is_processed_once(self):
        event = new_event("order.created", {"code": "CRY-1"}, "test")

        def apply(session, received):
            session.execute("INSERT INTO seen (id) VALUES (?)", (received["id"],))

        self.assertTrue(handle_once(self.consumer, event, apply))
        self.assertFalse(handle_once(self.consumer, json.loads(json.dumps(event)), apply))
        with self.consumer.session() as session:
            self.assertEqual(session.one("SELECT COUNT(*) FROM seen")[0], 1)


class ClientTest(unittest.TestCase):
    def test_breaker_opens_after_failures(self):
        breaker = CircuitBreaker(threshold=2, cooldown=60)
        breaker.failure()
        self.assertTrue(breaker.allow())
        breaker.failure()
        self.assertFalse(breaker.allow())
        breaker.success()
        self.assertTrue(breaker.allow())

    def test_unreachable_service_raises_upstream_error(self):
        client = ServiceClient("http://127.0.0.1:9", "yo‘q-servis", timeout=0.5, retries=0)
        with self.assertRaises(UpstreamError):
            client.get("/health")


if __name__ == "__main__":
    unittest.main()
