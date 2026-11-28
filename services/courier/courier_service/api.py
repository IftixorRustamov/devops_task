"""courier-service HTTP API."""

from http import HTTPStatus

from crystal_common import __version__
from crystal_common.health import register_health
from crystal_common.http import CODE, App
from crystal_common.security import ADMIN, COURIER, OPERATOR, require_role


def build_app(service, db, bus, relay):
    app = App("courier-service", __version__)
    register_health(app, db, bus, relay)

    @app.route("POST", rf"/api/v1/orders/{CODE}/assign")
    def assign(request, code):
        require_role(request, ADMIN, OPERATOR)
        body = request.json()
        return HTTPStatus.OK, service.assign(code, body.get("courier"))

    @app.route("GET", r"/api/v1/couriers/stats")
    def courier_stats(request):
        require_role(request, ADMIN, OPERATOR)
        return HTTPStatus.OK, {"items": service.stats()}

    @app.route("GET", r"/api/v1/couriers/me/assignments")
    def my_assignments(request):
        user = require_role(request, COURIER)
        return HTTPStatus.OK, {"items": service.list_for_courier(user.username)}

    @app.route("GET", rf"/internal/assignments/{CODE}")
    def assignment(_request, code):
        return HTTPStatus.OK, service.get_assignment(code)

    return app
