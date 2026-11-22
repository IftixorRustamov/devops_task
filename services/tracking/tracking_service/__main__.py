from crystal_common.bus import create_bus
from crystal_common.config import Settings
from crystal_common.db import Database
from crystal_common.logs import setup_logging
from crystal_common.runtime import serve

from .api import build_app
from .schema import SCHEMA
from .service import TrackingService

QUEUE = "tracking-service.events"
BINDINGS = ("order.*", "courier.assigned")


def main():
    settings = Settings("tracking", default_port=8003)
    setup_logging("tracking-service", settings.log_level)
    db = Database(settings.database_url)
    db.wait_until_ready(settings.startup_timeout)
    db.init_schema(SCHEMA)
    bus = create_bus(settings.broker_url, "tracking-service")
    service = TrackingService(db)
    bus.subscribe(QUEUE, BINDINGS, service.on_event)
    serve(build_app(service, db, bus), settings, background=[bus])


if __name__ == "__main__":
    main()
