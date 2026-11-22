import unittest

import _paths  # noqa: F401
from courier_service.schema import SCHEMA as COURIER_SCHEMA
from courier_service.service import CourierService
from crystal_common.errors import ConflictError, NotFoundError, ValidationError
from crystal_common.events import new_event
from helpers import FakeOrderClient, TempDatabases, clock
from tracking_service.schema import SCHEMA as TRACKING_SCHEMA
from tracking_service.service import TrackingService


class CourierServiceTest(unittest.TestCase):
    def setUp(self):
        self.dbs = TempDatabases()
        self.addCleanup(self.dbs.cleanup)
        self.orders = FakeOrderClient()
        self.service = CourierService(self.dbs.create("courier", COURIER_SCHEMA), self.orders, clock=clock)

    def test_assign_only_in_warehouse_and_only_once(self):
        self.orders.orders["CRY-1"] = "Yangi"
        with self.assertRaises(ConflictError):
            self.service.assign("CRY-1", "Ali")
        self.orders.orders["CRY-1"] = "Omborda"
        self.assertEqual(self.service.assign("cry-1", " Ali "), {"code": "CRY-1", "assigned": True})
        with self.assertRaises(ConflictError):
            self.service.assign("CRY-1", "Vali")
        self.assertEqual(self.service.get_assignment("CRY-1")["courier"], "Ali")

    def test_validation_and_not_found(self):
        with self.assertRaises(ValidationError):
            self.service.assign("CRY-1", "  ")
        with self.assertRaises(NotFoundError):
            self.service.assign("CRY-404", "Ali")
        with self.assertRaises(NotFoundError):
            self.service.get_assignment("CRY-404")

    def test_delivered_event_sets_delivered_at(self):
        self.orders.orders["CRY-1"] = "Omborda"
        self.service.assign("CRY-1", "Ali")
        event = new_event("order.status_changed", {"code": "CRY-1", "status": "Yetkazildi", "seq": 4}, "t")
        self.service.on_event(event)
        self.service.on_event(event)  # takror — xatosiz e’tiborsiz qoldiriladi
        self.assertEqual(self.service.get_assignment("CRY-1")["delivered_at"], event["occurred_at"])


class TrackingServiceTest(unittest.TestCase):
    def setUp(self):
        self.dbs = TempDatabases()
        self.addCleanup(self.dbs.cleanup)
        self.service = TrackingService(self.dbs.create("tracking", TRACKING_SCHEMA))

    def status_event(self, status, seq):
        kind = "order.created" if seq == 1 else "order.status_changed"
        return new_event(kind, {"code": "CRY-1", "status": status, "seq": seq}, "order-service")

    def test_builds_view_from_events(self):
        self.service.on_event(self.status_event("Yangi", 1))
        self.service.on_event(self.status_event("Omborda", 2))
        self.service.on_event(new_event("courier.assigned", {"code": "CRY-1", "courier": "Ali"}, "c"))
        result = self.service.track("cry-1")
        self.assertEqual(result["status"], "Omborda")
        self.assertTrue(result["courier_assigned"])
        self.assertEqual(len(result["timeline"]), 3)
        self.assertNotIn("Ali", str(result))  # kuryer nomi ommaviy javobda yo‘q

    def test_out_of_order_events_do_not_go_back(self):
        self.service.on_event(self.status_event("Omborda", 2))
        self.service.on_event(self.status_event("Yangi", 1))
        self.assertEqual(self.service.track("CRY-1")["status"], "Omborda")

    def test_courier_event_before_order_event(self):
        self.service.on_event(new_event("courier.assigned", {"code": "CRY-1", "courier": "Ali"}, "c"))
        with self.assertRaises(NotFoundError):
            self.service.track("CRY-1")
        self.service.on_event(self.status_event("Yangi", 1))
        self.assertTrue(self.service.track("CRY-1")["courier_assigned"])

    def test_duplicates_ignored(self):
        event = self.status_event("Yangi", 1)
        self.service.on_event(event)
        self.service.on_event(event)
        self.assertEqual(len(self.service.track("CRY-1")["timeline"]), 1)


if __name__ == "__main__":
    unittest.main()
