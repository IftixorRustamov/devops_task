"""Hodisalardan kuzatuv ko‘rinishini quradi.

Hodisalar kechikib yoki tartibsiz kelishi mumkin: joriy holat faqat `seq` kattaroq
bo‘lsa yangilanadi, shuning uchun eski hodisa yangi holatni bosib ketmaydi.
"""

from crystal_common.errors import NotFoundError, normalize_code
from crystal_common.events import handle_once

ORDER_EVENTS = ("order.created", "order.status_changed")
COURIER_ASSIGNED = "courier.assigned"


class TrackingService:
    def __init__(self, db):
        self.db = db

    def track(self, code):
        """Ommaviy javob: manzil va kuryer nomi yo‘q."""
        code = normalize_code(code)
        with self.db.session() as session:
            shipment = session.one(
                "SELECT status, courier_assigned, updated_at FROM shipments WHERE order_code = ?", (code,)
            )
            rows = session.all(
                "SELECT event_type, status, occurred_at FROM timeline WHERE order_code = ? "
                "ORDER BY occurred_at, event_id",
                (code,),
            )
        if shipment is None or shipment[0] is None:
            raise NotFoundError("Kuzatuv ma’lumoti topilmadi.")
        return {
            "code": code,
            "status": shipment[0],
            "courier_assigned": bool(shipment[1]),
            "updated_at": shipment[2],
            "timeline": [{"event": kind, "status": status, "at": at} for kind, status, at in rows],
        }

    # --- hodisalar ------------------------------------------------------------
    def on_event(self, event):
        handle_once(self.db, event, self._apply)

    def _apply(self, session, event):
        payload = event["payload"]
        code = payload["code"]
        at = event["occurred_at"]
        if event["type"] in ORDER_EVENTS:
            session.execute(
                "INSERT INTO shipments (order_code, status, seq, courier_assigned, updated_at) "
                "VALUES (?, ?, ?, 0, ?) "
                "ON CONFLICT (order_code) DO UPDATE SET status = excluded.status, seq = excluded.seq, "
                "updated_at = excluded.updated_at WHERE shipments.seq < excluded.seq",
                (code, payload["status"], payload["seq"], at),
            )
            status = payload["status"]
        elif event["type"] == COURIER_ASSIGNED:
            session.execute(
                "INSERT INTO shipments (order_code, status, seq, courier_assigned, updated_at) "
                "VALUES (?, NULL, 0, 1, ?) "
                "ON CONFLICT (order_code) DO UPDATE SET courier_assigned = 1",
                (code, at),
            )
            status = None
        else:
            return
        session.execute(
            "INSERT INTO timeline (event_id, order_code, event_type, status, occurred_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT (event_id) DO NOTHING",
            (event["id"], code, event["type"], status, at),
        )
