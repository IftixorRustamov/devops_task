"""tracking-db sxemasi."""

from crystal_common.events import INBOX_DDL

SCHEMA = """
CREATE TABLE IF NOT EXISTS shipments (
    order_code TEXT PRIMARY KEY,
    status TEXT,
    seq INTEGER NOT NULL,
    courier_assigned INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS timeline (
    event_id TEXT PRIMARY KEY,
    order_code TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS timeline_order ON timeline (order_code, occurred_at);
""" + INBOX_DDL
