"""tracking-service HTTP API."""

from http import HTTPStatus

from crystal_common import __version__
from crystal_common.health import register_health
from crystal_common.http import CODE, App


def build_app(service, db, bus):
    app = App("tracking-service", __version__)
    register_health(app, db, bus)

    @app.route("GET", rf"/api/v1/tracking/{CODE}")
    def track(_request, code):
        return HTTPStatus.OK, service.track(code)

    return app
