"""courier-service HTTP API."""

from http import HTTPStatus

from crystal_common import __version__
from crystal_common.health import register_health
from crystal_common.http import CODE, App


def build_app(service, db, bus, relay):
    app = App("courier-service", __version__)
    register_health(app, db, bus, relay)

    @app.route("POST", rf"/api/v1/orders/{CODE}/assign")
    def assign(request, code):
        body = request.json()
        return HTTPStatus.OK, service.assign(code, body.get("courier"))

    @app.route("GET", rf"/internal/assignments/{CODE}")
    def assignment(_request, code):
        return HTTPStatus.OK, service.get_assignment(code)

    return app
