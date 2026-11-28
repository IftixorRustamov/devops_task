"""auth-service HTTP API."""

from http import HTTPStatus

from crystal_common import __version__
from crystal_common.health import register_health
from crystal_common.http import App
from crystal_common.security import ADMIN, current_user, require_role

USERNAME = r"(?P<username>[A-Za-z0-9_.-]{1,64})"


def build_app(service, db):
    app = App("auth-service", __version__)
    register_health(app, db, bus=None)

    @app.route("POST", r"/api/v1/auth/login")
    def login(request):
        body = request.json()
        return HTTPStatus.OK, service.login(body.get("username"), body.get("password"))

    @app.route("POST", r"/api/v1/auth/refresh")
    def refresh(request):
        return HTTPStatus.OK, service.refresh(request.json().get("refresh_token"))

    @app.route("POST", r"/api/v1/auth/logout")
    def logout(request):
        return HTTPStatus.OK, service.logout(request.json().get("refresh_token"))

    @app.route("GET", r"/api/v1/auth/me")
    def me(request):
        return HTTPStatus.OK, service.get_user(current_user(request).username)

    @app.route("GET", r"/api/v1/auth/users")
    def list_users(request):
        require_role(request, ADMIN)
        return HTTPStatus.OK, {"items": service.list_users()}

    @app.route("POST", r"/api/v1/auth/users")
    def create_user(request):
        require_role(request, ADMIN)
        body = request.json()
        return HTTPStatus.CREATED, service.create_user(
            body.get("username"), body.get("password"), body.get("role")
        )

    @app.route("PATCH", rf"/api/v1/auth/users/{USERNAME}")
    def update_user(request, username):
        require_role(request, ADMIN)
        return HTTPStatus.OK, service.set_active(username, request.json().get("active"))

    # --- ichki (gateway va servislar uchun) -------------------------------------
    @app.route("GET", r"/internal/verify")
    def verify(request):
        payload, headers = service.verify(request.headers)
        return HTTPStatus.OK, payload, headers

    @app.route("GET", rf"/internal/users/{USERNAME}")
    def internal_user(_request, username):
        return HTTPStatus.OK, service.get_user(username)

    return app
