import logging
import secrets

from crystal_common.config import Settings, env, env_int
from crystal_common.db import Database
from crystal_common.logs import setup_logging
from crystal_common.runtime import serve

from .api import build_app
from .schema import SCHEMA
from .service import AuthService

log = logging.getLogger("crystal.auth")


def main():
    settings = Settings("auth", default_port=8004)
    setup_logging("auth-service", settings.log_level)
    secret = env("CRYSTAL_JWT_SECRET", "")
    if not secret:
        secret = secrets.token_urlsafe(48)
        log.warning("CRYSTAL_JWT_SECRET berilmagan — vaqtinchalik kalit yaratildi (restartda tokenlar bekor bo‘ladi).")
    db = Database(settings.database_url)
    db.wait_until_ready(settings.startup_timeout)
    db.init_schema(SCHEMA)
    service = AuthService(
        db, secret,
        access_ttl=env_int("CRYSTAL_ACCESS_TOKEN_TTL_S", 900),
        refresh_ttl=env_int("CRYSTAL_REFRESH_TOKEN_TTL_S", 7 * 24 * 3600),
    )
    admin_password = env("CRYSTAL_ADMIN_PASSWORD", "")
    if admin_password:
        service.ensure_admin(env("CRYSTAL_ADMIN_USERNAME", "admin"), admin_password)
    else:
        log.warning("CRYSTAL_ADMIN_PASSWORD berilmagan — boshlang‘ich admin yaratilmadi.")
    serve(build_app(service, db), settings)


if __name__ == "__main__":
    main()
