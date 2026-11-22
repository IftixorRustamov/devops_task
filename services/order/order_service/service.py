"""Buyurtma hayot sikli. Holat o‘zgarishi va hodisa bitta tranzaksiyada yoziladi (outbox)."""

from uuid import uuid4

from crystal_common.errors import (
    ConflictError, NotFoundError, UpstreamError, ValidationError, normalize_code, require_text,
)
from crystal_common.events import new_event, record_event, utc_now

from .domain import CODE_PREFIX, NEW, ORDER_CREATED, ORDER_STATUS_CHANGED, TRANSITIONS

SOURCE = "order-service"


class CourierClient:
    """courier-service bilan sinxron aloqa: buyurtmaga kuryer biriktirilganmi?"""

    def __init__(self, client):
        self.client = client

    def has_assignment(self, code):
        status, _payload = self.client.get(f"/internal/assignments/{code}")
        if status == 200:
            return True
        if status == 404:
            return False
        raise UpstreamError("courier-service kutilmagan javob qaytardi.")


class OrderService:
    def __init__(self, db, courier, clock=utc_now):
        self.db = db
        self.courier = courier
        self.clock = clock

    def list_warehouses(self):
        with self.db.session() as session:
            rows = session.all("SELECT id, name FROM warehouses ORDER BY id")
        return [{"id": row[0], "name": row[1]} for row in rows]

    def create_order(self, address, warehouse_id=1):
        address = require_text(address, "Manzil bo‘sh bo‘lmasligi kerak.", max_length=500)
        if isinstance(warehouse_id, bool) or not isinstance(warehouse_id, int):
            raise ValidationError("warehouse_id butun son bo‘lishi kerak.")
        code = CODE_PREFIX + uuid4().hex[:20].upper()
        now = self.clock()
        with self.db.session(write=True) as session:
            if session.one("SELECT 1 FROM warehouses WHERE id = ?", (warehouse_id,)) is None:
                raise ValidationError("Ombor topilmadi.")
            session.execute(
                "INSERT INTO orders (code, address, warehouse_id, status, version, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 1, ?, ?)",
                (code, address, warehouse_id, NEW, now, now),
            )
            session.execute(
                "INSERT INTO order_events (order_code, seq, status, created_at) VALUES (?, 1, ?, ?)",
                (code, NEW, now),
            )
            record_event(session, new_event(
                ORDER_CREATED,
                {"code": code, "warehouse_id": warehouse_id, "status": NEW, "seq": 1},
                SOURCE,
            ))
        return {"code": code, "status": NEW}

    def track(self, code):
        """Javob manzilni oshkor qilmaydi — kod bilan faqat holat ko‘rinadi."""
        code = normalize_code(code)
        with self.db.session() as session:
            rows = session.all(
                "SELECT status, created_at FROM order_events WHERE order_code = ? ORDER BY seq", (code,)
            )
        if not rows:
            raise NotFoundError("Buyurtma topilmadi.")
        history = [{"status": status, "created_at": created} for status, created in rows]
        return {"code": code, "status": history[-1]["status"], "history": history}

    def internal_view(self, code):
        """Boshqa servislar uchun (gateway orqali tashqariga ochilmaydi)."""
        code = normalize_code(code)
        with self.db.session() as session:
            row = session.one(
                "SELECT status, warehouse_id, version FROM orders WHERE code = ?", (code,)
            )
        if row is None:
            raise NotFoundError("Buyurtma topilmadi.")
        return {"code": code, "status": row[0], "warehouse_id": row[1], "version": row[2]}

    def move(self, code, action):
        if action not in TRANSITIONS:
            raise ValidationError(f"Noma’lum amal: {action}")
        code = normalize_code(code)
        previous, next_status = TRANSITIONS[action]
        if action == "dispatch":
            # Tarmoq so‘rovi tranzaksiyadan OLDIN: baza qulfi tashqi servisni kutib turmaydi.
            # Biriktirish o‘chirilmaydi, shuning uchun bu tekshiruv keyin ham haqiqiy qoladi.
            current = self.internal_view(code)["status"]
            if current == previous and not self.courier.has_assignment(code):
                raise ConflictError("Avval buyurtmaga kuryer biriktiring.")
        now = self.clock()
        with self.db.session(write=True) as session:
            row = session.one(
                "SELECT status, version FROM orders WHERE code = ?" + self.db.for_update, (code,)
            )
            if row is None:
                raise NotFoundError("Buyurtma topilmadi.")
            status, version = row
            if status != previous:
                raise ConflictError(f"Bu amal uchun buyurtma «{previous}» holatida bo‘lishi kerak.")
            seq = version + 1
            session.execute(
                "UPDATE orders SET status = ?, version = ?, updated_at = ? WHERE code = ?",
                (next_status, seq, now, code),
            )
            session.execute(
                "INSERT INTO order_events (order_code, seq, status, created_at) VALUES (?, ?, ?, ?)",
                (code, seq, next_status, now),
            )
            record_event(session, new_event(
                ORDER_STATUS_CHANGED,
                {"code": code, "status": next_status, "previous": previous, "seq": seq},
                SOURCE,
            ))
        return {"code": code, "status": next_status}
