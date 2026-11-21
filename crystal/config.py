"""Muhit o‘zgaruvchilaridan o‘qiladigan sozlamalar (12-factor)."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    db_path: str
    host: str
    port: int
    log_level: str

    @classmethod
    def from_env(cls, environ=None):
        env = os.environ if environ is None else environ
        port = env.get("CRYSTAL_PORT", "8000")
        if not port.isdigit() or not 0 < int(port) < 65536:
            raise ValueError(f"CRYSTAL_PORT noto‘g‘ri: {port!r}")
        return cls(
            db_path=env.get("CRYSTAL_DB_PATH", "crystal.sqlite3"),
            host=env.get("CRYSTAL_HOST", "127.0.0.1"),
            port=int(port),
            log_level=env.get("CRYSTAL_LOG_LEVEL", "INFO").upper(),
        )
