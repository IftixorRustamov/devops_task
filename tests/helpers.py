"""Testlar uchun yordamchilar: vaqtinchalik SQLite baza va soxta servis klientlari."""

from pathlib import Path
import tempfile

import _paths  # noqa: F401
from crystal_common.db import Database
from crystal_common.errors import NotFoundError


class TempDatabases:
    """Har bir servis uchun alohida SQLite fayl — production’dagi alohida bazalar kabi."""

    def __init__(self):
        self.folder = tempfile.TemporaryDirectory()

    def create(self, name, schema):
        db = Database(f"sqlite:///{Path(self.folder.name) / (name + '.sqlite3')}")
        db.init_schema(schema)
        return db

    def cleanup(self):
        self.folder.cleanup()


class FakeCourierClient:
    def __init__(self):
        self.assigned = set()

    def has_assignment(self, code):
        return code in self.assigned


class FakeOrderClient:
    def __init__(self):
        self.orders = {}

    def get_order(self, code):
        if code not in self.orders:
            raise NotFoundError("Buyurtma topilmadi.")
        return {"code": code, "status": self.orders[code]}


def clock():
    return "2026-11-22T10:00:00+00:00"
