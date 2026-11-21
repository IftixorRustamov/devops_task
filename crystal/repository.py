"""Ma’lumotlarga kirish qatlami: faqat SQL, biznes qoidalari yo‘q."""


class Repository:
    def __init__(self, db):
        self.db = db

    def warehouse_exists(self, warehouse_id):
        return self.db.execute(
            "SELECT 1 FROM warehouses WHERE id = ?", (warehouse_id,)
        ).fetchone() is not None

    def list_warehouses(self):
        rows = self.db.execute("SELECT id, name FROM warehouses ORDER BY id").fetchall()
        return [{"id": row[0], "name": row[1]} for row in rows]

    def insert_order(self, code, address, warehouse_id):
        self.db.execute(
            "INSERT INTO orders (code, address, warehouse_id) VALUES (?, ?, ?)",
            (code, address, warehouse_id),
        )

    def add_event(self, code, status, timestamp):
        self.db.execute(
            "INSERT INTO tracking_events (order_code, status, created_at) VALUES (?, ?, ?)",
            (code, status, timestamp),
        )

    def events(self, code):
        rows = self.db.execute(
            "SELECT status, created_at FROM tracking_events WHERE order_code = ? ORDER BY id",
            (code,),
        ).fetchall()
        return [{"status": status, "created_at": created} for status, created in rows]

    def has_delivery(self, code):
        return self.db.execute(
            "SELECT 1 FROM deliveries WHERE order_code = ?", (code,)
        ).fetchone() is not None

    def insert_delivery(self, code, courier, timestamp):
        self.db.execute(
            "INSERT INTO deliveries (order_code, courier, assigned_at) VALUES (?, ?, ?)",
            (code, courier, timestamp),
        )

    def mark_delivered(self, code, timestamp):
        self.db.execute(
            "UPDATE deliveries SET delivered_at = ? WHERE order_code = ?", (timestamp, code)
        )
