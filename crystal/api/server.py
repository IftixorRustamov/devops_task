"""Standart kutubxonadagi http.server asosidagi REST API.

Har bir so‘rov alohida oqimda ishlaydi va o‘z SQLite ulanishini oladi.
"""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import re
import signal
import threading
import time

from .. import __version__, db as database
from ..domain import ConflictError, NotFoundError, ValidationError
from ..service import OrderService

log = logging.getLogger("crystal.api")

MAX_BODY_BYTES = 64 * 1024
CODE = r"(?P<code>[A-Za-z0-9-]{1,64})"

# (metod, yo‘l shabloni, handler nomi)
ROUTES = [
    ("GET", r"/health", "health"),
    ("GET", r"/api/v1/warehouses", "list_warehouses"),
    ("POST", r"/api/v1/orders", "create_order"),
    ("GET", rf"/api/v1/orders/{CODE}", "track_order"),
    ("POST", rf"/api/v1/orders/{CODE}/assign", "assign_courier"),
    ("POST", rf"/api/v1/orders/{CODE}/(?P<action>receive|dispatch|deliver)", "move_order"),
]
COMPILED = [(method, re.compile(pattern + r"/?"), name) for method, pattern, name in ROUTES]

ERROR_STATUS = {
    ValidationError: HTTPStatus.BAD_REQUEST,
    NotFoundError: HTTPStatus.NOT_FOUND,
    ConflictError: HTTPStatus.CONFLICT,
}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    server_version = f"CrystalLogistics/{__version__}"
    protocol_version = "HTTP/1.1"

    # --- marshrutlash ---------------------------------------------------
    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_PATCH(self):
        self.dispatch("PATCH")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def dispatch(self, method):
        started = time.perf_counter()
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        path = self.path.split("?", 1)[0]
        try:
            handler, params = self.resolve(method, path)
            db = database.connect(self.server.db_path, init_schema=False)
            try:
                status, payload = handler(OrderService(db), **params)
            finally:
                db.close()
        except ApiError as error:
            status, payload = error.status, {"error": str(error)}
        except tuple(ERROR_STATUS) as error:
            status, payload = ERROR_STATUS[type(error)], {"error": str(error)}
        except Exception:
            log.exception("Kutilmagan xato: %s %s", method, path)
            status, payload = HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Ichki server xatosi."}
        self.send_json(status, payload)
        log.info(
            "%s %s %d %.1fms", method, path, status, (time.perf_counter() - started) * 1000
        )

    def resolve(self, method, path):
        allowed = False
        for route_method, pattern, name in COMPILED:
            match = pattern.fullmatch(path)
            if match:
                if route_method == method:
                    return getattr(self, name), match.groupdict()
                allowed = True
        if allowed:
            raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "Bu metod ruxsat etilmagan.")
        raise ApiError(HTTPStatus.NOT_FOUND, "Manzil topilmadi.")

    # --- yordamchilar ----------------------------------------------------
    def read_json(self):
        length = self.headers.get("Content-Length", "0")
        if not length.isdigit():
            raise ApiError(HTTPStatus.BAD_REQUEST, "Content-Length noto‘g‘ri.")
        if int(length) > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "So‘rov hajmi juda katta.")
        raw = self.rfile.read(int(length)) if int(length) else b"{}"
        try:
            body = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "So‘rov tanasi to‘g‘ri JSON emas.")
        if not isinstance(body, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "So‘rov tanasi JSON obyekt bo‘lishi kerak.")
        return body

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Standart stderr logini o‘chiramiz — o‘rniga dispatch() logging orqali yozadi."""

    # --- endpointlar -----------------------------------------------------
    def health(self, service):
        database.ping(service.db)
        return HTTPStatus.OK, {"status": "ok", "version": __version__}

    def list_warehouses(self, service):
        return HTTPStatus.OK, {"items": service.list_warehouses()}

    def create_order(self, service):
        body = self.read_json()
        result = service.create_order(body.get("address"), body.get("warehouse_id", 1))
        return HTTPStatus.CREATED, result

    def track_order(self, service, code):
        return HTTPStatus.OK, service.track(code)

    def assign_courier(self, service, code):
        body = self.read_json()
        return HTTPStatus.OK, service.assign(code, body.get("courier"))

    def move_order(self, service, code, action):
        return HTTPStatus.OK, service.move(code, action)


class CrystalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, db_path):
        self.db_path = db_path
        super().__init__(address, Handler)


def create_server(host, port, db_path):
    if db_path == ":memory:":
        raise ValueError("Server uchun fayldagi baza kerak (:memory: har ulanishda bo‘sh bo‘ladi).")
    database.connect(db_path).close()  # ishga tushishda sxema va papkani tayyorlash
    return CrystalServer((host, port), db_path)


def serve(settings):
    server = create_server(settings.host, settings.port, settings.db_path)

    def stop(signum, _frame):
        log.info("Signal %s olindi, server to‘xtatilmoqda", signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    host, port = server.server_address[:2]
    log.info("Crystal Logistics API %s:%s da ishlamoqda (db=%s)", host, port, settings.db_path)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        log.info("Server to‘xtadi")
