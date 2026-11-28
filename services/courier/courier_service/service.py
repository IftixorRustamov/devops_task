"""Kuryer biriktirish qoidalari."""

from crystal_common.errors import (
    ConflictError, NotFoundError, UpstreamError, ValidationError, normalize_code, require_text,
)
from crystal_common.events import handle_once, new_event, record_event, utc_now

SOURCE = "courier-service"
IN_WAREHOUSE = "Omborda"
DELIVERED = "Yetkazildi"
COURIER_ASSIGNED = "courier.assigned"


class OrderClient:
    """order-service bilan sinxron aloqa."""

    def __init__(self, client):
        self.client = client

    def get_order(self, code):
        status, payload = self.client.get(f"/internal/orders/{code}")
        if status == 200:
            return payload
        if status == 404:
            raise NotFoundError("Buyurtma topilmadi.")
        raise UpstreamError("order-service kutilmagan javob qaytardi.")


class AuthClient:
    """auth-service: kuryer logini mavjud, faol va roli `courier` ekanini tekshirish."""

    def __init__(self, client):
        self.client = client

    def is_active_courier(self, username):
        status, payload = self.client.get(f"/internal/users/{username}")
        if status == 200:
            return payload.get("role") == "courier" and payload.get("active") is True
        if status == 404:
            return False
        raise UpstreamError("auth-service kutilmagan javob qaytardi.")


class CourierService:
    def __init__(self, db, orders, auth, clock=utc_now):
        self.db = db
        self.orders = orders
        self.auth = auth
        self.clock = clock

    def assign(self, code, courier):
        code = normalize_code(code)
        courier = require_text(courier, "Kuryer logini bo‘sh bo‘lmasligi kerak.", max_length=32).lower()
        if not self.auth.is_active_courier(courier):
            raise ValidationError("Bunday faol kuryer yo‘q (login va `courier` rolini tekshiring).")
        order = self.orders.get_order(code)
        if order["status"] != IN_WAREHOUSE:
            raise ConflictError("Buyurtma omborga qabul qilingach kuryerga biriktiriladi.")
        with self.db.session(write=True) as session:
            cursor = session.execute(
                "INSERT INTO assignments (order_code, courier, assigned_at) VALUES (?, ?, ?) "
                "ON CONFLICT (order_code) DO NOTHING",
                (code, courier, self.clock()),
            )
            if cursor.rowcount == 0:
                raise ConflictError("Buyurtmaga kuryer allaqachon biriktirilgan.")
            record_event(session, new_event(COURIER_ASSIGNED, {"code": code, "courier": courier}, SOURCE))
        return {"code": code, "assigned": True}

    def get_assignment(self, code):
        code = normalize_code(code)
        with self.db.session() as session:
            row = session.one(
                "SELECT courier, assigned_at, delivered_at FROM assignments WHERE order_code = ?", (code,)
            )
        if row is None:
            raise NotFoundError("Biriktirish topilmadi.")
        return {"code": code, "courier": row[0], "assigned_at": row[1], "delivered_at": row[2]}

    def list_for_courier(self, courier):
        with self.db.session() as session:
            rows = session.all(
                "SELECT order_code, assigned_at, delivered_at FROM assignments WHERE courier = ? "
                "ORDER BY assigned_at DESC LIMIT 100",
                (courier,),
            )
        return [{"code": c, "assigned_at": a, "delivered_at": d} for c, a, d in rows]

    # --- hodisalar ------------------------------------------------------------
    def on_event(self, event):
        handle_once(self.db, event, self._apply)

    def _apply(self, session, event):
        payload = event["payload"]
        if event["type"] == "order.status_changed" and payload.get("status") == DELIVERED:
            session.execute(
                "UPDATE assignments SET delivered_at = ? WHERE order_code = ? AND delivered_at IS NULL",
                (event["occurred_at"], payload["code"]),
            )
