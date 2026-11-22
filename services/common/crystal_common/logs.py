"""Strukturali (JSON) loglar va so‘rov identifikatori (X-Request-ID).

Gateway har bir so‘rovga X-Request-ID beradi, servislar uni bir-biriga uzatadi —
bitta so‘rovning barcha servislardagi izini `docker compose logs | grep <id>` bilan topish mumkin.
"""

import json
import logging
import sys
import threading

_context = threading.local()


def set_request_id(value):
    _context.request_id = value


def get_request_id():
    return getattr(_context, "request_id", None)


class JsonFormatter(logging.Formatter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def format(self, record):
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = get_request_id()
        if request_id:
            entry["request_id"] = request_id
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(service, level="INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    logging.getLogger("pika").setLevel(logging.WARNING)
