"""order-service HTTP API."""

from http import HTTPStatus

from crystal_common import __version__
from crystal_common.health import register_health
from crystal_common.http import CODE, App


def build_app(service, db, bus, relay):
    app = App("order-service", __version__)
    register_health(app, db, bus, relay)

    @app.route("GET", r"/api/v1/warehouses")
    def list_warehouses(_request):
        return HTTPStatus.OK, {"items": service.list_warehouses()}

    @app.route("POST", r"/api/v1/orders")
    def create_order(request):
        body = request.json()
        return HTTPStatus.CREATED, service.create_order(body.get("address"), body.get("warehouse_id", 1))

    @app.route("GET", rf"/api/v1/orders/{CODE}")
    def track_order(_request, code):
        return HTTPStatus.OK, service.track(code)

    @app.route("POST", rf"/api/v1/orders/{CODE}/(?P<action>receive|dispatch|deliver)")
    def move_order(_request, code, action):
        return HTTPStatus.OK, service.move(code, action)

    @app.route("GET", rf"/internal/orders/{CODE}")
    def internal_order(_request, code):
        return HTTPStatus.OK, service.internal_view(code)

    return app
