"""Buyurtma hayot sikli. Holat o‘zgarishi va hodisa bitta tranzaksiyada yoziladi (outbox)."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from crystal_common.errors import (
    ConflictError, ForbiddenError, NotFoundError, UpstreamError, ValidationError, normalize_code,
    require_text,
)
from crystal_common.security import COURIER
from crystal_common.events import new_event, record_event, utc_now

from .domain import CODE_PREFIX, NEW, ORDER_CREATED, ORDER_STATUS_CHANGED, STATUSES, TRANSITIONS

SOURCE = "order-service"


def parse_time(value):
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


class CourierClient:
    """courier-service bilan sinxron aloqa: buyurtmaga kuryer biriktirilganmi?"""

    def __init__(self, client):
        self.client = client

    def assigned_courier(self, code):
        """Biriktirilgan kuryer logini yoki None."""
        status, payload = self.client.get(f"/internal/assignments/{code}")
        if status == 200:
            return payload["courier"]
        if status == 404:
            return None
        raise UpstreamError("courier-service kutilmagan javob qaytardi.")

    def has_assignment(self, code):
        return self.assigned_courier(code) is not None


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

    def stats(self, now=None, hours=24, recent=10, limit=5000):
        """Dashboard uchun ko‘rsatkichlar. Hisob Python’da — SQLite va PostgreSQL’da bir xil ishlaydi.
        Faqat oxirgi `limit` ta buyurtma olinadi (o‘quv loyihasi hajmi uchun yetarli)."""
        now = now or datetime.now(timezone.utc)
        with self.db.session() as session:
            orders = session.all(
                "SELECT code, status, created_at, updated_at FROM orders ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            codes = {row[0] for row in orders}
            events = session.all("SELECT order_code, seq, status, created_at FROM order_events ORDER BY order_code, seq")
        by_status = Counter(row[1] for row in orders)

        # Oxirgi `hours` soat: har soatda yaratilgan buyurtmalar (bo‘sh soatlar ham 0 bilan).
        start = (now - timedelta(hours=hours - 1)).replace(minute=0, second=0, microsecond=0)
        buckets = Counter()
        for _code, _status, created, _updated in orders:
            moment = parse_time(created)
            if moment and moment >= start:
                buckets[moment.replace(minute=0, second=0, microsecond=0)] += 1
        per_hour = [
            {"hour": (start + timedelta(hours=i)).isoformat(timespec="minutes"),
             "count": buckets[start + timedelta(hours=i)]}
            for i in range(hours)
        ]

        # Har bosqich o‘rtacha qancha davom etadi (ketma-ket hodisalar orasidagi vaqt).
        stage_seconds = {action: [] for action in TRANSITIONS}
        full_seconds = []
        by_order = {}
        for code, _seq, status, created in events:
            if code in codes:
                by_order.setdefault(code, []).append((status, parse_time(created)))
        status_to_action = {target: action for action, (_source, target) in TRANSITIONS.items()}
        for history in by_order.values():
            for (prev_status, prev_at), (status, at) in zip(history, history[1:]):
                if prev_at and at and status in status_to_action:
                    stage_seconds[status_to_action[status]].append((at - prev_at).total_seconds())
            if history[-1][0] == STATUSES[-1] and history[0][1] and history[-1][1]:
                full_seconds.append((history[-1][1] - history[0][1]).total_seconds())
        average = lambda values: round(sum(values) / len(values), 1) if values else None
        return {
            "total": len(orders),
            "by_status": {status: by_status.get(status, 0) for status in STATUSES},
            "created_per_hour": per_hour,
            "stage_avg_seconds": {action: average(values) for action, values in stage_seconds.items()},
            "delivery_avg_seconds": average(full_seconds),
            "recent": [
                {"code": c, "status": s, "created_at": ca, "updated_at": ua}
                for c, s, ca, ua in orders[:recent]
            ],
        }

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

    def move(self, code, action, actor=None):
        """`actor` — so‘rovni yuborgan foydalanuvchi. Kuryer faqat O‘ZIGA biriktirilgan
        buyurtmani topshira oladi."""
        if action not in TRANSITIONS:
            raise ValidationError(f"Noma’lum amal: {action}")
        code = normalize_code(code)
        previous, next_status = TRANSITIONS[action]
        if actor is not None and actor.role == COURIER:
            if action != "deliver":
                raise ForbiddenError("Kuryer faqat buyurtmani topshira oladi.")
            self.internal_view(code)  # mavjud bo‘lmasa 404
            if self.courier.assigned_courier(code) != actor.username:
                raise ForbiddenError("Bu buyurtma sizga biriktirilmagan.")
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
