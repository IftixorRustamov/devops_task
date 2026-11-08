import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import sqlite3
import sys
from uuid import uuid4


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

TRANSITIONS = {
    "receive": ("Yangi", "Omborda"),
    "dispatch": ("Omborda", "Yo‘lda"),
    "deliver": ("Yo‘lda", "Yetkazildi"),
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_event(db, code, status, timestamp):
    db.execute(
        "INSERT INTO tracking_events (order_code, status, created_at) VALUES (?, ?, ?)",
        (code, status, timestamp),
    )


def create_order(db, address, warehouse_id):
    address = address.strip()
    if not address:
        raise ValueError("Manzil bo‘sh bo‘lmasligi kerak.")
    if not db.execute("SELECT 1 FROM warehouses WHERE id = ?", (warehouse_id,)).fetchone():
        raise ValueError("Ombor topilmadi.")
    code = "CRY-" + uuid4().hex[:20].upper()
    db.execute(
        "INSERT INTO orders (code, address, warehouse_id) VALUES (?, ?, ?)",
        (code, address, warehouse_id),
    )
    append_event(db, code, "Yangi", now())
    return {"code": code, "status": "Yangi"}


def track(db, code):
    events = db.execute(
        "SELECT status, created_at FROM tracking_events WHERE order_code = ? ORDER BY id",
        (code,),
    ).fetchall()
    if not events:
        raise ValueError("Buyurtma topilmadi.")
    history = [{"status": status, "created_at": date} for status, date in events]
    return {"code": code, "status": history[-1]["status"], "history": history}


def assign(db, code, courier):
    if track(db, code)["status"] != "Omborda":
        raise ValueError("Buyurtma omborga qabul qilingach kuryerga biriktiriladi.")
    courier = courier.strip()
    if not courier:
        raise ValueError("Kuryer nomi bo‘sh bo‘lmasligi kerak.")
    if db.execute("SELECT 1 FROM deliveries WHERE order_code = ?", (code,)).fetchone():
        raise ValueError("Buyurtmaga kuryer allaqachon biriktirilgan.")
    db.execute(
        "INSERT INTO deliveries (order_code, courier, assigned_at) VALUES (?, ?, ?)",
        (code, courier, now()),
    )
    return {"code": code, "assigned": True}


def move(db, code, command):
    previous, next_status = TRANSITIONS[command]
    if track(db, code)["status"] != previous:
        raise ValueError(f"Bu amal uchun buyurtma «{previous}» holatida bo‘lishi kerak.")
    if command == "dispatch" and not db.execute(
        "SELECT 1 FROM deliveries WHERE order_code = ?", (code,)
    ).fetchone():
        raise ValueError("Avval buyurtmaga kuryer biriktiring.")
    timestamp = now()
    append_event(db, code, next_status, timestamp)
    if command == "deliver":
        db.execute(
            "UPDATE deliveries SET delivered_at = ? WHERE order_code = ?",
            (timestamp, code),
        )
    return {"code": code, "status": next_status}


def main():
    parser = argparse.ArgumentParser(description="Crystal Logistics")
    parser.add_argument("--db", default="crystal.sqlite3", help="SQLite fayli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Buyurtmani yaratishdan topshirishgacha ko‘rsatish")
    create = commands.add_parser("create", help="Buyurtma yaratish")
    create.add_argument("address")
    create.add_argument("--warehouse", type=int, default=1)
    for name in ("receive", "assign", "dispatch", "deliver", "track"):
        command = commands.add_parser(name)
        command.add_argument("code")
        if name == "assign":
            command.add_argument("courier")
    args = parser.parse_args()
    db_path = ":memory:" if args.command == "demo" else args.db

    try:
        with closing(sqlite3.connect(db_path)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            db.executescript(SCHEMA)
            with db:
                if args.command == "track":
                    result = track(db, args.code.strip().upper())
                else:
                    db.execute("BEGIN IMMEDIATE")
                    if args.command == "demo":
                        code = create_order(db, "Demo manzil", 1)["code"]
                        move(db, code, "receive")
                        assign(db, code, "Demo kuryer")
                        move(db, code, "dispatch")
                        move(db, code, "deliver")
                        result = track(db, code)
                    elif args.command == "create":
                        result = create_order(db, args.address, args.warehouse)
                    elif args.command == "assign":
                        result = assign(db, args.code.strip().upper(), args.courier)
                    else:
                        result = move(db, args.code.strip().upper(), args.command)
    except (ValueError, sqlite3.Error) as error:
        print(error, file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
