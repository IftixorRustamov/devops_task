"""Baza adapteri: production’da PostgreSQL, testlarda SQLite.

Har bir servis O‘Z bazasiga ulanadi (database-per-service). Servis boshqa
servisning jadvaliga hech qachon to‘g‘ridan-to‘g‘ri murojaat qilmaydi —
faqat HTTP API yoki hodisalar (events) orqali.

SQL `?` belgisi bilan yoziladi; PostgreSQL uchun avtomatik `%s` ga aylantiriladi.
Shu sababli SQL matnida `?` va `%` belgilarini literal sifatida ishlatmang.
"""

from contextlib import contextmanager
import logging
import os
import sqlite3
import time

log = logging.getLogger("crystal.db")

SQLITE = "sqlite"
POSTGRES = "postgres"


class Session:
    """Bitta tranzaksiya ichidagi ulanish."""

    def __init__(self, connection, dialect):
        self.connection = connection
        self.dialect = dialect

    def execute(self, sql, params=()):
        if self.dialect == POSTGRES:
            sql = sql.replace("?", "%s")
        return self.connection.execute(sql, tuple(params))

    def one(self, sql, params=()):
        return self.execute(sql, params).fetchone()

    def all(self, sql, params=()):
        return self.execute(sql, params).fetchall()


class Database:
    def __init__(self, url):
        self.url = url
        if url.startswith("sqlite:///"):
            self.dialect = SQLITE
            self.path = url[len("sqlite:///"):]
            if self.path in ("", ":memory:"):
                raise ValueError("Servis uchun fayldagi SQLite kerak (:memory: har ulanishda bo‘sh).")
        elif url.startswith(("postgres://", "postgresql://")):
            self.dialect = POSTGRES
            self.path = None
        else:
            raise ValueError("Noma’lum baza manzili (sqlite:/// yoki postgresql:// kutilgan).")

    # --- qulflash qo‘shimchalari ----------------------------------------------
    @property
    def for_update(self):
        """Tekshirish va yozish orasida qatorni boshqa so‘rovlardan qulflaydi.
        SQLite’da butun baza `BEGIN IMMEDIATE` bilan qulflanadi."""
        return " FOR UPDATE" if self.dialect == POSTGRES else ""

    @property
    def skip_locked(self):
        """Bir nechta replika outbox’ni parallel o‘qiganda bir xabarni ikki marta olmaslik uchun."""
        return " FOR UPDATE SKIP LOCKED" if self.dialect == POSTGRES else ""

    # --- ulanish --------------------------------------------------------------
    def _connect(self):
        if self.dialect == POSTGRES:
            import psycopg  # faqat konteynerda o‘rnatilgan; testlar SQLite ishlatadi

            return psycopg.connect(self.url, autocommit=True, connect_timeout=5)
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def session(self, write=False):
        connection = self._connect()
        try:
            if self.dialect == SQLITE:
                connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            else:
                connection.execute("BEGIN")
            session = Session(connection, self.dialect)
            try:
                yield session
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
        finally:
            connection.close()

    # --- sxema va holat -------------------------------------------------------
    def init_schema(self, ddl):
        statements = [part.strip() for part in ddl.split(";") if part.strip()]
        with self.session(write=True) as session:
            if self.dialect == POSTGRES:
                # Bir nechta replika bir vaqtda ishga tushsa sxemani faqat bittasi yaratadi.
                session.execute("SELECT pg_advisory_xact_lock(7290001)")
            for statement in statements:
                session.execute(statement)

    def migrate(self, migrations):
        """Versiyalangan migratsiyalar: `[(versiya, {"postgres": [...], "sqlite": [...]})]`.

        Qo‘llangan versiyalar `schema_migrations` jadvalida saqlanadi, har biri bir marta
        bajariladi. Yangi baza asosiy sxemadan to‘liq yaratiladi, shuning uchun migratsiyalar
        idempotent yoziladi (`IF NOT EXISTS`). SQLite faqat testlarda — u har doim yangi.
        """
        from .events import utc_now  # aylanma importdan qochish

        with self.session(write=True) as session:
            if self.dialect == POSTGRES:
                session.execute("SELECT pg_advisory_xact_lock(7290002)")
            session.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {row[0] for row in session.all("SELECT version FROM schema_migrations")}
            for version, steps in migrations:
                if version in applied:
                    continue
                for statement in steps.get(self.dialect, []):
                    session.execute(statement)
                session.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, utc_now())
                )
                log.info("Migratsiya qo‘llandi: v%s", version)

    def ping(self):
        with self.session() as session:
            return session.one("SELECT 1")[0] == 1

    def wait_until_ready(self, timeout=60):
        deadline = time.monotonic() + timeout
        delay = 0.5
        while True:
            try:
                self.ping()
                return
            except Exception as error:  # baza hali ko‘tarilmagan bo‘lishi mumkin
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Baza {timeout} s ichida tayyor bo‘lmadi: {error}")
                log.warning("Baza tayyor emas, %.1f s dan keyin qayta urinish: %s", delay, error)
                time.sleep(delay)
                delay = min(delay * 2, 5)
