"""Servisni ishga tushirish: bazani kutish, sxema, fon oqimlari, graceful shutdown."""

import logging
import signal
import threading

from .http import make_server

log = logging.getLogger("crystal.runtime")


def serve(app, settings, background=()):
    """HTTP serverni ishga tushiradi. `background` — start()/stop() metodli obyektlar."""
    server = make_server(app, settings.host, settings.port)

    def stop(signum, _frame):
        log.info("Signal %s olindi, servis to‘xtatilmoqda", signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    for component in background:
        component.start()
    log.info("%s ishga tushdi: %s", app.name, settings.safe_dict())
    try:
        server.serve_forever()
    finally:
        for component in reversed(list(background)):
            component.stop()
        server.server_close()
        log.info("%s to‘xtadi", app.name)
