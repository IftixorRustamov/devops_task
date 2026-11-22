"""Hodisalar, Transactional Outbox va idempotent Inbox.

Outbox: servis o‘z bazasidagi o‘zgarish va hodisani BITTA tranzaksiyada yozadi.
Alohida oqim (OutboxRelay) yozilgan hodisalarni RabbitMQ’ga yuboradi. Shu tufayli
“bazaga yozildi, lekin xabar yo‘qoldi” holati bo‘lmaydi (at-least-once).

Inbox: qabul qiluvchi servis har bir hodisa `id`sini `processed_events`ga yozadi.
Bir xil hodisa ikki marta kelsa, ikkinchisi e’tiborsiz qoldiriladi.
"""

from datetime import datetime, timezone
import json
import logging
import threading
from uuid import uuid4

log = logging.getLogger("crystal.events")

OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS outbox (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS outbox_pending ON outbox (published_at, created_at);
"""

INBOX_DDL = """
CREATE TABLE IF NOT EXISTS processed_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    processed_at TEXT NOT NULL
);
"""


def utc_now(precise=False):
    return datetime.now(timezone.utc).isoformat(timespec="microseconds" if precise else "seconds")


def new_event(event_type, payload, source):
    return {
        "id": str(uuid4()),
        "type": event_type,
        "source": source,
        "occurred_at": utc_now(precise=True),
        "payload": payload,
    }


def record_event(session, event):
    """Hodisani joriy tranzaksiya ichida outbox’ga yozadi."""
    session.execute(
        "INSERT INTO outbox (id, event_type, body, created_at) VALUES (?, ?, ?, ?)",
        (event["id"], event["type"], json.dumps(event, ensure_ascii=False), event["occurred_at"]),
    )


def pending_count(db):
    with db.session() as session:
        return session.one("SELECT COUNT(*) FROM outbox WHERE published_at IS NULL")[0]


class OutboxRelay:
    def __init__(self, db, bus, interval=0.5, batch_size=100):
        self.db = db
        self.bus = bus
        self.interval = interval
        self.batch_size = batch_size
        self._stop = threading.Event()
        self._thread = None

    def run_once(self):
        """Yuborilmagan hodisalarni shinaga chiqaradi. Yuborilganlar sonini qaytaradi."""
        sent = 0
        with self.db.session(write=True) as session:
            rows = session.all(
                "SELECT id, body FROM outbox WHERE published_at IS NULL "
                "ORDER BY created_at, id LIMIT ?" + self.db.skip_locked,
                (self.batch_size,),
            )
            for event_id, body in rows:
                self.bus.publish(json.loads(body))
                session.execute(
                    "UPDATE outbox SET published_at = ? WHERE id = ?", (utc_now(True), event_id)
                )
                sent += 1
        return sent

    def _loop(self):
        while not self._stop.is_set():
            try:
                while self.run_once() == self.batch_size and not self._stop.is_set():
                    pass
            except Exception as error:
                # Shina yoki baza vaqtincha ishlamayapti — hodisalar outbox’da kutadi.
                log.warning("Outbox relay xatosi, keyinroq qayta urinadi: %s", error)
                self._stop.wait(min(self.interval * 4, 5))
            self._stop.wait(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="outbox-relay", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def is_alive(self):
        return self._thread is not None and self._thread.is_alive()


def handle_once(db, event, handler):
    """Hodisani idempotent qayta ishlaydi. Yangi bo‘lsa True, takror bo‘lsa False."""
    with db.session(write=True) as session:
        cursor = session.execute(
            "INSERT INTO processed_events (event_id, event_type, processed_at) VALUES (?, ?, ?) "
            "ON CONFLICT (event_id) DO NOTHING",
            (event["id"], event["type"], utc_now(True)),
        )
        if cursor.rowcount == 0:
            log.info("Takroriy hodisa o‘tkazib yuborildi: %s %s", event["type"], event["id"])
            return False
        handler(session, event)
    return True
