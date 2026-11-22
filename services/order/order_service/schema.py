"""order-db sxemasi. PostgreSQL va SQLite’da bir xil ishlaydi."""

from crystal_common.events import OUTBOX_DDL

SCHEMA = """
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS orders (
    code TEXT PRIMARY KEY,
    address TEXT NOT NULL,
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    status TEXT NOT NULL CHECK (status IN ('Yangi', 'Omborda', 'Yo‘lda', 'Yetkazildi')),
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_events (
    order_code TEXT NOT NULL REFERENCES orders(code),
    seq INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (order_code, seq)
);
INSERT INTO warehouses (id, name) VALUES (1, 'Markaziy ombor') ON CONFLICT (id) DO NOTHING;
""" + OUTBOX_DDL
