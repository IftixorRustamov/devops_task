"""Biznes mantiq: buyurtmaning hayot sikli. CLI ham, HTTP API ham shu qatlamni chaqiradi."""

from datetime import datetime, timezone
from uuid import uuid4

from . import db as database
from .domain import (
    CODE_PREFIX, IN_WAREHOUSE, NEW, TRANSITIONS,
    ConflictError, NotFoundError, ValidationError, normalize_code, require_text,
)
from .repository import Repository


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class OrderService:
    def __init__(self, db, clock=utc_now):
        self.db = db
        self.repo = Repository(db)
        self.clock = clock

    def list_warehouses(self):
        return self.repo.list_warehouses()

    def create_order(self, address, warehouse_id=1):
        address = require_text(address, "Manzil bo‘sh bo‘lmasligi kerak.")
        if isinstance(warehouse_id, bool) or not isinstance(warehouse_id, int):
            raise ValidationError("warehouse_id butun son bo‘lishi kerak.")
        with database.transaction(self.db):
            if not self.repo.warehouse_exists(warehouse_id):
                raise ValidationError("Ombor topilmadi.")
            code = CODE_PREFIX + uuid4().hex[:20].upper()
            self.repo.insert_order(code, address, warehouse_id)
            self.repo.add_event(code, NEW, self.clock())
        return {"code": code, "status": NEW}

    def track(self, code):
        """Kuzatuv javobi manzil va kuryer nomini oshkor qilmaydi (docs/decisions.md)."""
        code = normalize_code(code)
        history = self.repo.events(code)
        if not history:
            raise NotFoundError("Buyurtma topilmadi.")
        return {"code": code, "status": history[-1]["status"], "history": history}

    def assign(self, code, courier):
        code = normalize_code(code)
        courier = require_text(courier, "Kuryer nomi bo‘sh bo‘lmasligi kerak.")
        with database.transaction(self.db):
            if self.track(code)["status"] != IN_WAREHOUSE:
                raise ConflictError("Buyurtma omborga qabul qilingach kuryerga biriktiriladi.")
            if self.repo.has_delivery(code):
                raise ConflictError("Buyurtmaga kuryer allaqachon biriktirilgan.")
            self.repo.insert_delivery(code, courier, self.clock())
        return {"code": code, "assigned": True}

    def move(self, code, action):
        if action not in TRANSITIONS:
            raise ValidationError(f"Noma’lum amal: {action}")
        code = normalize_code(code)
        previous, next_status = TRANSITIONS[action]
        with database.transaction(self.db):
            if self.track(code)["status"] != previous:
                raise ConflictError(f"Bu amal uchun buyurtma «{previous}» holatida bo‘lishi kerak.")
            if action == "dispatch" and not self.repo.has_delivery(code):
                raise ConflictError("Avval buyurtmaga kuryer biriktiring.")
            timestamp = self.clock()
            self.repo.add_event(code, next_status, timestamp)
            if action == "deliver":
                self.repo.mark_delivered(code, timestamp)
        return {"code": code, "status": next_status}

    def run_demo(self):
        code = self.create_order("Demo manzil", 1)["code"]
        self.move(code, "receive")
        self.assign(code, "Demo kuryer")
        self.move(code, "dispatch")
        self.move(code, "deliver")
        return self.track(code)
