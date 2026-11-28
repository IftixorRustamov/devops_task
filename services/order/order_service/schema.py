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
    recipient_name TEXT NOT NULL DEFAULT '',
    recipient_phone TEXT NOT NULL DEFAULT '',
    cancel_reason TEXT,
    status TEXT NOT NULL CHECK (status IN ('Yangi', 'Omborda', 'Yo‘lda', 'Yetkazildi', 'Bekor qilindi')),
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
CREATE INDEX IF NOT EXISTS orders_status_created ON orders (status, created_at);
INSERT INTO warehouses (id, name) VALUES (1, 'Markaziy ombor') ON CONFLICT (id) DO NOTHING;
""" + OUTBOX_DDL


# Mavjud bazalarni yangilash (masalan, Codespaces’dagi ma’lumotlar o‘chmasligi uchun).
MIGRATIONS = [
    (2, {
        "postgres": [
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS recipient_name TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS recipient_phone TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancel_reason TEXT",
            "ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check",
            "ALTER TABLE orders ADD CONSTRAINT orders_status_check CHECK "
            "(status IN ('Yangi', 'Omborda', 'Yo‘lda', 'Yetkazildi', 'Bekor qilindi'))",
            "CREATE INDEX IF NOT EXISTS orders_status_created ON orders (status, created_at)",
        ],
    }),
]
