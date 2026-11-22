"""Kuryer biriktirish qoidalari."""

from crystal_common.errors import ConflictError, NotFoundError, UpstreamError, normalize_code, require_text
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


class CourierService:
    def __init__(self, db, orders, clock=utc_now):
        self.db = db
        self.orders = orders
        self.clock = clock

    def assign(self, code, courier):
        code = normalize_code(code)
        courier = require_text(courier, "Kuryer nomi bo‘sh bo‘lmasligi kerak.")
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
