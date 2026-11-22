from crystal_common.bus import create_bus
from crystal_common.config import Settings, env
from crystal_common.db import Database
from crystal_common.events import OutboxRelay
from crystal_common.http import ServiceClient
from crystal_common.logs import setup_logging
from crystal_common.runtime import serve

from .api import build_app
from .schema import SCHEMA
from .service import CourierClient, OrderService


def main():
    settings = Settings("order", default_port=8001)
    setup_logging("order-service", settings.log_level)
    db = Database(settings.database_url)
    db.wait_until_ready(settings.startup_timeout)
    db.init_schema(SCHEMA)
    bus = create_bus(settings.broker_url, "order-service")
    relay = OutboxRelay(db, bus, settings.outbox_interval)
    courier = CourierClient(ServiceClient(
        env("CRYSTAL_COURIER_SERVICE_URL", "http://localhost:8002"), "courier-service", settings.http_timeout,
    ))
    app = build_app(OrderService(db, courier), db, bus, relay)
    serve(app, settings, background=[bus, relay])


if __name__ == "__main__":
    main()
