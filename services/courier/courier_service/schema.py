"""courier-db sxemasi."""

from crystal_common.events import INBOX_DDL, OUTBOX_DDL

SCHEMA = """
CREATE TABLE IF NOT EXISTS assignments (
    order_code TEXT PRIMARY KEY,
    courier TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    delivered_at TEXT
);
CREATE INDEX IF NOT EXISTS assignments_courier ON assignments (courier, assigned_at);
""" + OUTBOX_DDL + INBOX_DDL
