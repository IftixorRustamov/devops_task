from crystal_common.bus import create_bus
from crystal_common.config import Settings, env
from crystal_common.db import Database
from crystal_common.events import OutboxRelay
from crystal_common.http import ServiceClient
from crystal_common.logs import setup_logging
from crystal_common.runtime import serve

from .api import build_app
from .schema import SCHEMA
from .service import CourierService, OrderClient

QUEUE = "courier-service.events"
BINDINGS = ("order.status_changed",)


def main():
    settings = Settings("courier", default_port=8002)
    setup_logging("courier-service", settings.log_level)
    db = Database(settings.database_url)
    db.wait_until_ready(settings.startup_timeout)
    db.init_schema(SCHEMA)
    bus = create_bus(settings.broker_url, "courier-service")
    relay = OutboxRelay(db, bus, settings.outbox_interval)
    orders = OrderClient(ServiceClient(
        env("CRYSTAL_ORDER_SERVICE_URL", "http://localhost:8001"), "order-service", settings.http_timeout,
    ))
    service = CourierService(db, orders)
    bus.subscribe(QUEUE, BINDINGS, service.on_event)
    serve(build_app(service, db, bus, relay), settings, background=[bus, relay])


if __name__ == "__main__":
    main()
