"""SQLite ulanishi va sxema."""

from contextlib import contextmanager
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS orders (
    code TEXT PRIMARY KEY,
    address TEXT NOT NULL,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id)
);
CREATE TABLE IF NOT EXISTS deliveries (
    order_code TEXT PRIMARY KEY REFERENCES orders(code),
    courier TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    delivered_at TEXT
);
CREATE TABLE IF NOT EXISTS tracking_events (
    id INTEGER PRIMARY KEY,
    order_code TEXT NOT NULL REFERENCES orders(code),
    status TEXT NOT NULL CHECK (status IN ('Yangi', 'Omborda', 'Yo‘lda', 'Yetkazildi')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tracking_events_order ON tracking_events(order_code, id);
INSERT OR IGNORE INTO warehouses (id, name) VALUES (1, 'Markaziy ombor');
"""


def connect(path, init_schema=True):
    """Yangi ulanish ochadi. init_schema=True bo‘lsa sxemani ham tayyorlaydi (ishga tushishda bir marta)."""
    if path != ":memory:":
        folder = os.path.dirname(os.path.abspath(path))
        os.makedirs(folder, exist_ok=True)
    db = sqlite3.connect(path, timeout=5, isolation_level=None)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    if path != ":memory:":
        db.execute("PRAGMA journal_mode = WAL")
    if init_schema:
        db.executescript(SCHEMA)
    return db


@contextmanager
def transaction(db, write=True):
    """Yozish amallari BEGIN IMMEDIATE bilan boshlanadi — parallel so‘rovlar navbatga turadi."""
    db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    try:
        yield db
    except BaseException:
        db.execute("ROLLBACK")
        raise
    db.execute("COMMIT")


def ping(db):
    return db.execute("SELECT 1").fetchone()[0] == 1
