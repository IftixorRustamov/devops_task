"""Standart kutubxona asosidagi kichik HTTP karkas va servislararo klient.

Server: marshrutlash, JSON, xato kodlari, so‘rov hajmi cheklovi, X-Request-ID.
Klient: timeout, qayta urinish (faqat GET), oddiy circuit breaker.
"""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from .errors import DomainError, UpstreamError
from .logs import get_request_id, set_request_id

log = logging.getLogger("crystal.http")

MAX_BODY_BYTES = 64 * 1024
CODE = r"(?P<code>[A-Za-z0-9-]{1,64})"


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Request:
    def __init__(self, method, path, headers, body, query=None):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query = query or {}

    def arg(self, name, default=None):
        """Query parametri (`?status=Yangi`), birinchi qiymat."""
        values = self.query.get(name)
        return values[0] if values else default

    def json(self):
        raw = self.body or b"{}"
        try:
            data = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "So‘rov tanasi to‘g‘ri JSON emas.")
        if not isinstance(data, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "So‘rov tanasi JSON obyekt bo‘lishi kerak.")
        return data


class App:
    """Marshrutlar to‘plami. Handler `(request, **params) -> (status, payload)` qaytaradi."""

    def __init__(self, name, version):
        self.name = name
        self.version = version
        self.routes = []

    def route(self, method, pattern):
        compiled = re.compile(pattern + r"/?")

        def register(function):
            self.routes.append((method, compiled, function))
            return function

        return register

    def resolve(self, method, path):
        allowed = False
        for route_method, pattern, function in self.routes:
            match = pattern.fullmatch(path)
            if match:
                if route_method == method:
                    return function, match.groupdict()
                allowed = True
        if allowed:
            raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "Bu metod ruxsat etilmagan.")
        raise ApiError(HTTPStatus.NOT_FOUND, "Manzil topilmadi.")

    def handle(self, request):
        """`(status, payload, headers)` qaytaradi. Handler 2 yoki 3 elementli tuple qaytarishi mumkin."""
        try:
            function, params = self.resolve(request.method, request.path)
            result = function(request, **params)
        except ApiError as error:
            result = error.status, {"error": str(error)}
        except DomainError as error:
            result = error.status, {"error": str(error)}
        except Exception:
            log.exception("Kutilmagan xato: %s %s", request.method, request.path)
            result = HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Ichki server xatosi."}
        if len(result) == 2:
            return result[0], result[1], {}
        return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _read_body(self):
        length = self.headers.get("Content-Length", "0")
        if not length.isdigit():
            raise ApiError(HTTPStatus.BAD_REQUEST, "Content-Length noto‘g‘ri.")
        if int(length) > MAX_BODY_BYTES:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "So‘rov hajmi juda katta.")
        return self.rfile.read(int(length)) if int(length) else b""

    def _dispatch(self, method):
        started = time.perf_counter()
        set_request_id(self.headers.get("X-Request-ID") or uuid4().hex)
        path, _, raw_query = self.path.partition("?")
        try:
            query = urllib.parse.parse_qs(raw_query, max_num_fields=20)
            request = Request(method, path, self.headers, self._read_body(), query)
            status, payload, headers = self.server.app.handle(request)
        except ApiError as error:
            status, payload, headers = error.status, {"error": str(error)}, {}
            self.close_connection = True
        self._send_json(status, payload, headers)
        level = logging.DEBUG if path == "/health" else logging.INFO
        log.log(level, "%s %s %d %.1fms", method, path, status, (time.perf_counter() - started) * 1000)
        set_request_id(None)

    def _send_json(self, status, payload, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-ID", get_request_id() or "")
        self.send_header("X-Service", self.server.app.name)
        self.end_headers()
        self.wfile.write(body)

    def version_string(self):
        return f"crystal-{self.server.app.name}/{self.server.app.version}"

    def log_message(self, format, *args):
        """Standart stderr logi o‘chirilgan — _dispatch() JSON log yozadi."""


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, app):
        self.app = app
        super().__init__(address, Handler)


def make_server(app, host, port):
    return Server((host, port), app)


class CircuitBreaker:
    """Ketma-ket `threshold` marta xato bo‘lsa `cooldown` soniya davomida so‘rov yubormaydi."""

    def __init__(self, threshold=5, cooldown=10):
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = 0
        self.opened_at = None
        self._lock = threading.Lock()

    def allow(self):
        with self._lock:
            if self.opened_at is None:
                return True
            if time.monotonic() - self.opened_at >= self.cooldown:
                return True  # half-open: bitta sinov so‘roviga ruxsat
            return False

    def success(self):
        with self._lock:
            self.failures = 0
            self.opened_at = None

    def failure(self):
        with self._lock:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = time.monotonic()


class ServiceClient:
    def __init__(self, base_url, name, timeout=3.0, retries=2):
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.timeout = timeout
        self.retries = retries
        self.breaker = CircuitBreaker()

    def request(self, method, path, body=None):
        if not self.breaker.allow():
            raise UpstreamError(f"{self.name} servisi vaqtincha mavjud emas.")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if get_request_id():
            headers["X-Request-ID"] = get_request_id()
        attempts = 1 + (self.retries if method == "GET" else 0)  # POST takrorlanmaydi
        last_error = None
        for attempt in range(attempts):
            request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read() or b"{}")
                    self.breaker.success()
                    return response.status, payload
            except urllib.error.HTTPError as error:
                if error.code >= 500:
                    last_error = error
                else:
                    self.breaker.success()
                    try:
                        payload = json.loads(error.read() or b"{}")
                    except ValueError:
                        payload = {}
                    return error.code, payload
            except (urllib.error.URLError, OSError, ValueError) as error:
                last_error = error
            if attempt + 1 < attempts:
                time.sleep(0.2 * (attempt + 1))
        self.breaker.failure()
        log.warning("%s servisiga so‘rov muvaffaqiyatsiz: %s %s: %s", self.name, method, path, last_error)
        raise UpstreamError(f"{self.name} servisi javob bermadi.")

    def get(self, path):
        return self.request("GET", path)
