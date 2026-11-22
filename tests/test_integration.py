"""Uchta servis haqiqiy HTTP orqali, har biri o‘z bazasi bilan, bitta jarayonda.

RabbitMQ o‘rniga xotiradagi shina; outbox relay qo‘lda (`flush`) ishga tushiriladi —
shu tufayli test deterministik. To‘liq stack (PostgreSQL + RabbitMQ + nginx) CI’da
docker compose bilan tekshiriladi.
"""

import http.client
import json
import threading
import unittest

import _paths  # noqa: F401
from courier_service.api import build_app as courier_app
from courier_service.schema import SCHEMA as COURIER_SCHEMA
from courier_service.service import CourierService, OrderClient
from crystal_common.bus import InMemoryBus
from crystal_common.events import OutboxRelay
from crystal_common.http import ServiceClient, make_server
from helpers import TempDatabases
from order_service.api import build_app as order_app
from order_service.schema import SCHEMA as ORDER_SCHEMA
from order_service.service import CourierClient, OrderService
from tracking_service.api import build_app as tracking_app
from tracking_service.schema import SCHEMA as TRACKING_SCHEMA
from tracking_service.service import TrackingService


class Stack:
    def __init__(self):
        self.dbs = TempDatabases()
        self.bus = InMemoryBus()
        self.servers = []
        order_db = self.dbs.create("order", ORDER_SCHEMA)
        courier_db = self.dbs.create("courier", COURIER_SCHEMA)
        tracking_db = self.dbs.create("tracking", TRACKING_SCHEMA)
        self.order_relay = OutboxRelay(order_db, self.bus)
        self.courier_relay = OutboxRelay(courier_db, self.bus)

        # Portlar oldindan kerak bo‘lgani uchun serverlar avval yaratiladi, app keyin ulanadi.
        self.order_server = self._server()
        self.courier_server = self._server()
        self.tracking_server = self._server()
        order_url = f"http://127.0.0.1:{self.order_server.server_address[1]}"
        courier_url = f"http://127.0.0.1:{self.courier_server.server_address[1]}"

        orders = OrderService(order_db, CourierClient(ServiceClient(courier_url, "courier", 2)))
        couriers = CourierService(courier_db, OrderClient(ServiceClient(order_url, "order", 2)))
        tracking = TrackingService(tracking_db)
        self.bus.subscribe("courier-service.events", ("order.status_changed",), couriers.on_event)
        self.bus.subscribe("tracking-service.events", ("order.*", "courier.assigned"), tracking.on_event)

        self.order_server.app = order_app(orders, order_db, self.bus, self.order_relay)
        self.courier_server.app = courier_app(couriers, courier_db, self.bus, self.courier_relay)
        self.tracking_server.app = tracking_app(tracking, tracking_db, self.bus)
        self.order_relay.start = self.courier_relay.start = lambda: None  # sog‘liq tekshiruvi uchun
        self.order_relay.is_alive = self.courier_relay.is_alive = lambda: True
        for server in self.servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()

    def _server(self):
        server = make_server(None, "127.0.0.1", 0)
        self.servers.append(server)
        return server

    def flush(self):
        self.order_relay.run_once()
        self.courier_relay.run_once()

    def close(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()
        self.dbs.cleanup()


def call(server, method, path, body=None, raw=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    try:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        all_headers = {"Content-Type": "application/json"} if data is not None else {}
        all_headers.update(headers or {})
        connection.request(method, path, body=data, headers=all_headers)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload, response
    finally:
        connection.close()


class IntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = Stack()

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()

    def test_full_lifecycle_across_services(self):
        s = self.stack
        status, created, _ = call(s.order_server, "POST", "/api/v1/orders", {"address": "Chilonzor 1"})
        self.assertEqual(status, 201)
        code = created["code"]

        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/receive")[0], 200)
        # dispatch: courier-service’ga sinxron so‘rov -> biriktirish yo‘q -> 409
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/dispatch")[0], 409)
        # assign: courier-service order-service’dan holatni so‘raydi
        status, payload, _ = call(s.courier_server, "POST", f"/api/v1/orders/{code}/assign", {"courier": "Ali"})
        self.assertEqual((status, payload), (200, {"code": code, "assigned": True}))
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/dispatch")[0], 200)
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/deliver")[0], 200)
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/deliver")[0], 409)

        status, order, _ = call(s.order_server, "GET", f"/api/v1/orders/{code}")
        self.assertEqual(order["status"], "Yetkazildi")

        # Hodisalar hali yuborilmagan: tracking-service buyurtmani bilmaydi (eventual consistency).
        self.assertEqual(call(s.tracking_server, "GET", f"/api/v1/tracking/{code}")[0], 404)
        s.flush()
        status, tracked, _ = call(s.tracking_server, "GET", f"/api/v1/tracking/{code}")
        self.assertEqual(status, 200)
        self.assertEqual(tracked["status"], "Yetkazildi")
        self.assertTrue(tracked["courier_assigned"])
        self.assertNotIn("Ali", json.dumps(tracked, ensure_ascii=False))
        self.assertNotIn("Chilonzor", json.dumps(tracked, ensure_ascii=False))

        _, assignment, _ = call(s.courier_server, "GET", f"/internal/assignments/{code}")
        self.assertIsNotNone(assignment["delivered_at"])

    def test_assign_conflicts_and_not_found(self):
        s = self.stack
        _, created, _ = call(s.order_server, "POST", "/api/v1/orders", {"address": "Yunusobod"})
        code = created["code"]
        self.assertEqual(call(s.courier_server, "POST", f"/api/v1/orders/{code}/assign", {"courier": "Ali"})[0], 409)
        self.assertEqual(call(s.courier_server, "POST", "/api/v1/orders/CRY-NONE/assign", {"courier": "Ali"})[0], 404)
        self.assertEqual(call(s.courier_server, "POST", f"/api/v1/orders/{code}/assign", {})[0], 400)

    def test_http_errors(self):
        s = self.stack
        self.assertEqual(call(s.order_server, "GET", "/api/v1/orders/CRY-NONE")[0], 404)
        self.assertEqual(call(s.order_server, "GET", "/nope")[0], 404)
        self.assertEqual(call(s.order_server, "DELETE", "/api/v1/orders")[0], 405)
        self.assertEqual(call(s.order_server, "POST", "/api/v1/orders", raw=b"{bad")[0], 400)
        self.assertEqual(call(s.order_server, "POST", "/api/v1/orders", raw=b"[]")[0], 400)
        self.assertEqual(call(s.order_server, "POST", "/api/v1/orders", raw=b"x" * (64 * 1024 + 1))[0], 413)

    def test_health_and_request_id(self):
        for server in self.stack.servers:
            status, payload, _ = call(server, "GET", "/health")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["checks"]["database"], "ok")
        _, _, response = call(self.stack.order_server, "GET", "/health", headers={"X-Request-ID": "abc123"})
        self.assertEqual(response.getheader("X-Request-ID"), "abc123")
        self.assertEqual(response.getheader("X-Service"), "order-service")

    def test_dispatch_returns_503_when_courier_service_down(self):
        s = self.stack
        _, created, _ = call(s.order_server, "POST", "/api/v1/orders", {"address": "Sergeli"})
        code = created["code"]
        call(s.order_server, "POST", f"/api/v1/orders/{code}/receive")
        original = s.order_server.app  # courier klientini ishlamaydigan manzilga almashtiramiz
        orders = OrderService(
            s.order_relay.db, CourierClient(ServiceClient("http://127.0.0.1:9", "courier", 0.3, retries=0))
        )
        s.order_server.app = order_app(orders, s.order_relay.db, s.bus, s.order_relay)
        try:
            status, payload, _ = call(s.order_server, "POST", f"/api/v1/orders/{code}/dispatch")
        finally:
            s.order_server.app = original
        self.assertEqual(status, 503)
        self.assertIn("courier", payload["error"])


if __name__ == "__main__":
    unittest.main()
