"""Umumiy /health endpointi.

- Baza ishlamasa: 503 (servis so‘rovlarni bajara olmaydi).
- Faqat broker ishlamasa: 200 + "degraded". Outbox tufayli servis yozishda davom etadi,
  hodisalar broker qaytgach yuboriladi.
"""

from http import HTTPStatus
import logging

log = logging.getLogger("crystal.health")


def register_health(app, db, bus, relay=None, extra=None):
    @app.route("GET", r"/health")
    def health(_request):
        checks = {}
        try:
            checks["database"] = "ok" if db.ping() else "fail"
        except Exception as error:
            log.warning("Baza tekshiruvi muvaffaqiyatsiz: %s", error)
            checks["database"] = "fail"
        checks["broker"] = "ok" if bus.healthy() else "fail"
        if relay is not None:
            checks["outbox_relay"] = "ok" if relay.is_alive() else "fail"
        if extra:
            for name, function in extra.items():
                try:
                    checks[name] = function()
                except Exception:
                    checks[name] = "fail"
        if checks["database"] != "ok":
            status, overall = HTTPStatus.SERVICE_UNAVAILABLE, "fail"
        elif "fail" in checks.values():
            status, overall = HTTPStatus.OK, "degraded"
        else:
            status, overall = HTTPStatus.OK, "ok"
        return status, {"status": overall, "service": app.name, "version": app.version, "checks": checks}

    return health
