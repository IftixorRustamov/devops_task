import unittest

import _paths  # noqa: F401
from crystal_common.errors import ConflictError, NotFoundError, ValidationError
from crystal_common.events import pending_count
from crystal_common.errors import ForbiddenError
from helpers import FakeCourierClient, TempDatabases, User, clock
from order_service.schema import SCHEMA
from order_service.service import OrderService


class OrderServiceTest(unittest.TestCase):
    def setUp(self):
        self.dbs = TempDatabases()
        self.addCleanup(self.dbs.cleanup)
        self.db = self.dbs.create("order", SCHEMA)
        self.courier = FakeCourierClient()
        self.service = OrderService(self.db, self.courier, clock=clock)

    def create(self):
        return self.service.create_order("Demo manzil")["code"]

    def test_full_lifecycle_and_history(self):
        code = self.create()
        self.service.move(code, "receive")
        self.courier.assigned[code] = "ali"
        self.service.move(code, "dispatch")
        self.service.move(code, "deliver")
        result = self.service.track(code.lower())
        self.assertEqual(result["status"], "Yetkazildi")
        self.assertEqual([h["status"] for h in result["history"]],
                         ["Yangi", "Omborda", "Yo‘lda", "Yetkazildi"])
        self.assertNotIn("address", result)
        self.assertEqual(self.service.internal_view(code)["version"], 4)

    def test_every_change_writes_one_outbox_event(self):
        code = self.create()
        self.service.move(code, "receive")
        self.assertEqual(pending_count(self.db), 2)

    def test_code_format(self):
        code = self.create()
        self.assertTrue(code.startswith("CRY-"))
        self.assertEqual(len(code), 24)

    def test_validation(self):
        for address in ("", "   ", None, 5, "x" * 501):
            with self.assertRaises(ValidationError):
                self.service.create_order(address)
        for warehouse in ("1", True, 99):
            with self.assertRaises(ValidationError):
                self.service.create_order("Manzil", warehouse)
        with self.assertRaises(ValidationError):
            self.service.move(self.create(), "teleport")

    def test_steps_cannot_be_skipped_or_repeated(self):
        code = self.create()
        with self.assertRaises(ConflictError):
            self.service.move(code, "dispatch")
        with self.assertRaises(ConflictError):
            self.service.move(code, "deliver")
        self.service.move(code, "receive")
        with self.assertRaises(ConflictError):
            self.service.move(code, "receive")

    def test_dispatch_requires_courier(self):
        code = self.create()
        self.service.move(code, "receive")
        with self.assertRaises(ConflictError):
            self.service.move(code, "dispatch")
        self.assertEqual(pending_count(self.db), 2)  # muvaffaqiyatsiz amal hodisa yozmaydi

    def test_unknown_order(self):
        with self.assertRaises(NotFoundError):
            self.service.track("CRY-UNKNOWN")
        with self.assertRaises(NotFoundError):
            self.service.move("CRY-UNKNOWN", "receive")

    def test_courier_can_only_deliver_own_order(self):
        code = self.create()
        self.service.move(code, "receive")
        self.courier.assigned[code] = "ali"
        with self.assertRaises(ForbiddenError):
            self.service.move(code, "dispatch", actor=User("ali", "courier"))
        self.service.move(code, "dispatch", actor=User("op", "operator"))
        with self.assertRaises(ForbiddenError):
            self.service.move(code, "deliver", actor=User("vali", "courier"))
        self.assertEqual(self.service.move(code, "deliver", actor=User("ali", "courier"))["status"], "Yetkazildi")

    def test_stats(self):
        times = iter([
            "2026-11-28T10:00:00+00:00", "2026-11-28T10:10:00+00:00",
            "2026-11-28T10:30:00+00:00", "2026-11-28T11:00:00+00:00",
            "2026-11-28T11:05:00+00:00",
        ])
        self.service.clock = lambda: next(times)
        code = self.create()
        self.service.move(code, "receive")
        self.courier.assigned[code] = "ali"
        self.service.move(code, "dispatch")
        self.service.move(code, "deliver")
        self.create()  # ikkinchi buyurtma: Yangi
        from datetime import datetime, timezone
        stats = self.service.stats(now=datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["by_status"], {"Yangi": 1, "Omborda": 0, "Yo‘lda": 0, "Yetkazildi": 1})
        self.assertEqual(stats["stage_avg_seconds"], {"receive": 600.0, "dispatch": 1200.0, "deliver": 1800.0})
        self.assertEqual(stats["delivery_avg_seconds"], 3600.0)
        self.assertEqual(len(stats["created_per_hour"]), 24)
        self.assertEqual(sum(h["count"] for h in stats["created_per_hour"]), 2)
        self.assertEqual(stats["recent"][0]["status"], "Yangi")

    def test_warehouses_seeded(self):
        self.assertEqual(self.service.list_warehouses(), [{"id": 1, "name": "Markaziy ombor"}])


if __name__ == "__main__":
    unittest.main()
