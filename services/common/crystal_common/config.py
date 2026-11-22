"""Muhit o‘zgaruvchilaridan sozlamalarni o‘qish (CRYSTAL_*)."""

import os


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Muhit o‘zgaruvchisi kerak: {name}")
    return value


def env_int(name, default):
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"{name} butun son bo‘lishi kerak, berilgan: {raw!r}")


class Settings:
    """Har bir servis uchun bir xil nomlangan asosiy sozlamalar."""

    def __init__(self, service, default_port=8000):
        self.service = service
        self.host = env("CRYSTAL_HOST", "0.0.0.0")
        self.port = env_int("CRYSTAL_PORT", default_port)
        self.database_url = env("CRYSTAL_DATABASE_URL", f"sqlite:///{service}.sqlite3")
        # Bo‘sh bo‘lsa xotiradagi shina ishlatiladi (faqat lokal ishga tushirish uchun).
        self.broker_url = env("CRYSTAL_BROKER_URL", "")
        self.log_level = env("CRYSTAL_LOG_LEVEL", "INFO").upper()
        self.http_timeout = env_int("CRYSTAL_HTTP_TIMEOUT_MS", 3000) / 1000
        self.outbox_interval = env_int("CRYSTAL_OUTBOX_INTERVAL_MS", 500) / 1000
        self.startup_timeout = env_int("CRYSTAL_STARTUP_TIMEOUT_S", 60)

    def safe_dict(self):
        """Logga chiqarish uchun: parollar yashiriladi."""
        return {
            "service": self.service,
            "port": self.port,
            "database": mask_url(self.database_url),
            "broker": mask_url(self.broker_url) or "in-memory",
        }


def mask_url(url):
    if not url or "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"
