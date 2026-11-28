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
from auth_service.api import build_app as auth_app
from auth_service.schema import SCHEMA as AUTH_SCHEMA
from auth_service.service import AuthService
from courier_service.api import build_app as courier_app
from courier_service.schema import SCHEMA as COURIER_SCHEMA
from courier_service.service import AuthClient, CourierService, OrderClient
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
        auth_db = self.dbs.create("auth", AUTH_SCHEMA)
        self.auth = AuthService(auth_db, "t" * 40, password_iterations=1000)
        self.auth.ensure_admin("admin", "admin-parol-123")
        self.auth.create_user("ali", "ali-parol-123", "courier")
        self.auth.create_user("vali", "vali-parol-123", "courier")
        self.order_relay = OutboxRelay(order_db, self.bus)
        self.courier_relay = OutboxRelay(courier_db, self.bus)

        # Portlar oldindan kerak bo‘lgani uchun serverlar avval yaratiladi, app keyin ulanadi.
        self.order_server = self._server()
        self.courier_server = self._server()
        self.tracking_server = self._server()
        self.auth_server = self._server()
        auth_url = f"http://127.0.0.1:{self.auth_server.server_address[1]}"
        order_url = f"http://127.0.0.1:{self.order_server.server_address[1]}"
        courier_url = f"http://127.0.0.1:{self.courier_server.server_address[1]}"

        orders = OrderService(order_db, CourierClient(ServiceClient(courier_url, "courier", 2)))
        couriers = CourierService(
            courier_db,
            OrderClient(ServiceClient(order_url, "order", 2)),
            AuthClient(ServiceClient(auth_url, "auth", 2)),
        )
        tracking = TrackingService(tracking_db)
        self.bus.subscribe("courier-service.events", ("order.status_changed",), couriers.on_event)
        self.bus.subscribe("tracking-service.events", ("order.*", "courier.assigned"), tracking.on_event)

        self.order_server.app = order_app(orders, order_db, self.bus, self.order_relay)
        self.courier_server.app = courier_app(couriers, courier_db, self.bus, self.courier_relay)
        self.tracking_server.app = tracking_app(tracking, tracking_db, self.bus)
        self.auth_server.app = auth_app(self.auth, auth_db)
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


OPERATOR = {"X-User": "op", "X-User-Role": "operator"}  # gateway qo‘yadigan sarlavhalar
ALI = {"X-User": "ali", "X-User-Role": "courier"}
VALI = {"X-User": "vali", "X-User-Role": "courier"}
ADMIN = {"X-User": "admin", "X-User-Role": "admin"}


def call(server, method, path, body=None, raw=None, headers=None, as_user=OPERATOR):
    if as_user:
        headers = dict(as_user, **(headers or {}))
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
        status, created, _ = call(s.order_server, "POST", "/api/v1/orders", {"address": "Chilonzor 1", "recipient_name": "Aziza", "recipient_phone": "901234567"})
        self.assertEqual(status, 201)
        code = created["code"]

        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/receive")[0], 200)
        # dispatch: courier-service’ga sinxron so‘rov -> biriktirish yo‘q -> 409
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/dispatch")[0], 409)
        # assign: courier-service order-service’dan holatni so‘raydi
        status, payload, _ = call(s.courier_server, "POST", f"/api/v1/orders/{code}/assign", {"courier": "ali"})
        self.assertEqual((status, payload), (200, {"code": code, "assigned": True}))
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/dispatch")[0], 200)
        # Boshqa kuryer topshira olmaydi, biriktirilgan kuryer — topshiradi.
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/deliver", as_user=VALI)[0], 403)
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/deliver", as_user=ALI)[0], 200)
        _, mine, _ = call(s.courier_server, "GET", "/api/v1/couriers/me/assignments", as_user=ALI)
        self.assertEqual(mine["items"][0]["code"], code)
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/deliver")[0], 409)

        status, order, _ = call(s.order_server, "GET", f"/api/v1/orders/{code}")
        self.assertEqual((order["status"], order["courier"], order["recipient_phone"]), ("Yetkazildi", "ali", "+998901234567"))
        self.assertEqual(call(s.order_server, "GET", f"/api/v1/orders/{code}", as_user=VALI)[0], 403)
        self.assertEqual(call(s.order_server, "GET", f"/api/v1/orders/{code}", as_user=ALI)[0], 200)
        status, found, _ = call(s.order_server, "GET", "/api/v1/orders?q=chilonzor&status=Yetkazildi&limit=5")
        self.assertEqual((status, found["items"][0]["code"]), (200, code))

        # Hodisalar hali yuborilmagan: tracking-service buyurtmani bilmaydi (eventual consistency).
        self.assertEqual(call(s.tracking_server, "GET", f"/api/v1/tracking/{code}")[0], 404)
        s.flush()
        status, tracked, _ = call(s.tracking_server, "GET", f"/api/v1/tracking/{code}")
        self.assertEqual(status, 200)
        self.assertEqual(tracked["status"], "Yetkazildi")
        self.assertTrue(tracked["courier_assigned"])
        self.assertNotIn("ali", json.dumps(tracked, ensure_ascii=False))
        self.assertNotIn("Chilonzor", json.dumps(tracked, ensure_ascii=False))
        self.assertNotIn("901234567", json.dumps(tracked, ensure_ascii=False))

        _, assignment, _ = call(s.courier_server, "GET", f"/internal/assignments/{code}")
        self.assertIsNotNone(assignment["delivered_at"])

    def test_stats_endpoints_are_staff_only(self):
        s = self.stack
        self.assertEqual(call(s.order_server, "GET", "/api/v1/stats")[0], 200)
        self.assertEqual(call(s.order_server, "GET", "/api/v1/stats", as_user=ALI)[0], 403)
        status, payload, _ = call(s.courier_server, "GET", "/api/v1/couriers/stats")
        self.assertEqual(status, 200)
        self.assertIn("items", payload)
        self.assertEqual(call(s.courier_server, "GET", "/api/v1/couriers/stats", as_user=ALI)[0], 403)

    def test_cancel_reaches_tracking(self):
        s = self.stack
        _, created, _ = call(s.order_server, "POST", "/api/v1/orders", {"address": "Olmazor", "recipient_name": "Aziza", "recipient_phone": "901234567"})
        code = created["code"]
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/cancel", {"reason": "Mijoz"}, as_user=ALI)[0], 403)
        self.assertEqual(call(s.order_server, "POST", f"/api/v1/orders/{code}/cancel", {"reason": "Mijoz"})[0], 200)
        s.flush()
        self.assertEqual(call(s.tracking_server, "GET", f"/api/v1/tracking/{code}", as_user=None)[1]["status"], "Bekor qilindi")
        self.assertEqual(call(s.order_server, "GET", "/api/v1/orders?status=Noma%E2%80%99lum")[0], 400)

    def test_assign_conflicts_and_not_found(self):
        s = self.stack
        _, created, _ = call(s.order_server, "POST", "/api/v1/orders", {"address": "Yunusobod", "recipient_name": "Aziza", "recipient_phone": "901234567"})
        code = created["code"]
        self.assertEqual(call(s.courier_server, "POST", f"/api/v1/orders/{code}/assign", {"courier": "ali"})[0], 409)
        self.assertEqual(call(s.courier_server, "POST", "/api/v1/orders/CRY-NONE/assign", {"courier": "ali"})[0], 404)
        self.assertEqual(call(s.courier_server, "POST", f"/api/v1/orders/{code}/assign", {"courier": "admin"})[0], 400)
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
            status, payload, _ = call(server, "GET", "/health", as_user=None)
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["checks"]["database"], "ok")
        _, _, response = call(self.stack.order_server, "GET", "/health", headers={"X-Request-ID": "abc123"})
        self.assertEqual(response.getheader("X-Request-ID"), "abc123")
        self.assertEqual(response.getheader("X-Service"), "order-service")

    def test_dispatch_returns_503_when_courier_service_down(self):
        s = self.stack
        _, created, _ = call(s.order_server, "POST", "/api/v1/orders", {"address": "Sergeli", "recipient_name": "Aziza", "recipient_phone": "901234567"})
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


class AuthIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = Stack()

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()

    def login(self, username, password):
        return call(self.stack.auth_server, "POST", "/api/v1/auth/login",
                    {"username": username, "password": password}, as_user=None)

    def test_no_identity_means_401_and_wrong_role_403(self):
        s = self.stack
        self.assertEqual(call(s.order_server, "POST", "/api/v1/orders", {"address": "x", "recipient_name": "Aziza", "recipient_phone": "901234567"}, as_user=None)[0], 401)
        self.assertEqual(call(s.order_server, "POST", "/api/v1/orders", {"address": "x", "recipient_name": "Aziza", "recipient_phone": "901234567"}, as_user=ALI)[0], 403)
        self.assertEqual(call(s.courier_server, "POST", "/api/v1/orders/CRY-1/assign", {"courier": "ali"},
                              as_user=ALI)[0], 403)
        self.assertEqual(call(s.auth_server, "GET", "/api/v1/auth/users", as_user=OPERATOR)[0], 403)
        self.assertEqual(call(s.auth_server, "GET", "/api/v1/auth/users", as_user=ADMIN)[0], 200)
        # Kuzatuv ommaviy — token kerak emas.
        self.assertEqual(call(s.tracking_server, "GET", "/api/v1/tracking/CRY-NONE", as_user=None)[0], 404)

    def test_login_verify_refresh_logout(self):
        s = self.stack
        self.assertEqual(self.login("ali", "noto‘g‘ri-parol")[0], 401)
        self.assertEqual(self.login("yoq-user", "noto‘g‘ri-parol")[0], 401)
        status, tokens, _ = self.login("ALI", "ali-parol-123")
        self.assertEqual(status, 200)
        self.assertEqual(tokens["user"], {"username": "ali", "role": "courier"})

        # Gateway shunday tekshiradi: token -> X-User / X-User-Role sarlavhalari.
        bearer = {"Authorization": "Bearer " + tokens["access_token"]}
        status, _, response = call(s.auth_server, "GET", "/internal/verify", headers=bearer, as_user=None)
        self.assertEqual(status, 200)
        self.assertEqual((response.getheader("X-User"), response.getheader("X-User-Role")), ("ali", "courier"))
        tampered = {"Authorization": "Bearer " + tokens["access_token"][:-2] + "xx"}
        self.assertEqual(call(s.auth_server, "GET", "/internal/verify", headers=tampered, as_user=None)[0], 401)
        self.assertEqual(call(s.auth_server, "GET", "/internal/verify", as_user=None)[0], 401)

        status, renewed, _ = call(s.auth_server, "POST", "/api/v1/auth/refresh",
                                  {"refresh_token": tokens["refresh_token"]}, as_user=None)
        self.assertEqual(status, 200)
        self.assertNotEqual(renewed["refresh_token"], tokens["refresh_token"])
        # Eski refresh token qayta ishlatildi -> rad etiladi va barcha sessiyalar bekor bo‘ladi.
        self.assertEqual(call(s.auth_server, "POST", "/api/v1/auth/refresh",
                              {"refresh_token": tokens["refresh_token"]}, as_user=None)[0], 401)
        self.assertEqual(call(s.auth_server, "POST", "/api/v1/auth/refresh",
                              {"refresh_token": renewed["refresh_token"]}, as_user=None)[0], 401)

        _, again, _ = self.login("ali", "ali-parol-123")
        call(s.auth_server, "POST", "/api/v1/auth/logout", {"refresh_token": again["refresh_token"]}, as_user=None)
        self.assertEqual(call(s.auth_server, "POST", "/api/v1/auth/refresh",
                              {"refresh_token": again["refresh_token"]}, as_user=None)[0], 401)

    def test_admin_manages_users(self):
        s = self.stack
        status, user, _ = call(s.auth_server, "POST", "/api/v1/auth/users",
                               {"username": "g_ani", "password": "uzun-parol-1", "role": "courier"}, as_user=ADMIN)
        self.assertEqual((status, user["role"]), (201, "courier"))
        self.assertEqual(call(s.auth_server, "POST", "/api/v1/auth/users",
                              {"username": "g_ani", "password": "uzun-parol-1", "role": "courier"},
                              as_user=ADMIN)[0], 409)
        self.assertEqual(call(s.auth_server, "POST", "/api/v1/auth/users",
                              {"username": "x", "password": "qisqa", "role": "boss"}, as_user=ADMIN)[0], 400)
        self.assertEqual(call(s.auth_server, "PATCH", "/api/v1/auth/users/g_ani", {"active": False},
                              as_user=ADMIN)[0], 200)
        self.assertEqual(self.login("g_ani", "uzun-parol-1")[0], 401)
        _, me, _ = call(s.auth_server, "GET", "/api/v1/auth/me", as_user=ALI)
        self.assertEqual(me["role"], "courier")
