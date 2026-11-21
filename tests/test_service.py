from contextlib import closing
import unittest

from crystal import db as database
from crystal.domain import ConflictError, NotFoundError, ValidationError
from crystal.service import OrderService


class OrderServiceTest(unittest.TestCase):
    def setUp(self):
        self.db = database.connect(":memory:")
        self.addCleanup(self.db.close)
        self.service = OrderService(self.db, clock=lambda: "2026-11-21T10:00:00+00:00")

    def new_order(self):
        return self.service.create_order("Test manzil", 1)["code"]

    def test_full_lifecycle(self):
        code = self.new_order()
        self.service.move(code, "receive")
        self.service.assign(code, "Test kuryer")
        self.service.move(code, "dispatch")
        self.assertEqual(self.service.move(code, "deliver")["status"], "Yetkazildi")
        delivered_at = self.db.execute(
            "SELECT delivered_at FROM deliveries WHERE order_code = ?", (code,)
        ).fetchone()[0]
        self.assertEqual(delivered_at, "2026-11-21T10:00:00+00:00")

    def test_code_is_case_insensitive(self):
        code = self.new_order()
        self.assertEqual(self.service.track(f"  {code.lower()} ")["code"], code)

    def test_steps_cannot_be_skipped(self):
        code = self.new_order()
        with self.assertRaises(ConflictError):
            self.service.move(code, "dispatch")
        with self.assertRaises(ConflictError):
            self.service.assign(code, "Kuryer")

    def test_courier_assigned_only_once(self):
        code = self.new_order()
        self.service.move(code, "receive")
        self.service.assign(code, "Birinchi")
        with self.assertRaises(ConflictError):
            self.service.assign(code, "Ikkinchi")

    def test_failed_action_rolls_back(self):
        code = self.new_order()
        self.service.move(code, "receive")
        with self.assertRaises(ConflictError):
            self.service.move(code, "dispatch")
        self.assertEqual(len(self.service.track(code)["history"]), 2)

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.service.create_order("   ")
        with self.assertRaises(ValidationError):
            self.service.create_order("Manzil", 999)
        with self.assertRaises(ValidationError):
            self.service.create_order("Manzil", "1")
        with self.assertRaises(ValidationError):
            self.service.create_order(None)

    def test_unknown_order(self):
        with self.assertRaises(NotFoundError):
            self.service.track("CRY-NOPE")

    def test_warehouses_seeded(self):
        self.assertEqual(self.service.list_warehouses(), [{"id": 1, "name": "Markaziy ombor"}])


class ConnectionTest(unittest.TestCase):
    def test_file_database_creates_parent_folder(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "nested", "data.sqlite3")
            with closing(database.connect(path)) as db:
                self.assertTrue(database.ping(db))
            self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
