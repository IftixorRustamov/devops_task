"""Autentifikatsiya va avtorizatsiya: JWT (HS256), parol xeshi, rollar.

Oqim:
    1. Mijoz `POST /api/v1/auth/login` -> access token (JWT, 15 daqiqa) + refresh token.
    2. Har bir so‘rovda `Authorization: Bearer <access token>`.
    3. Gateway (nginx `auth_request`) tokenni auth-service’ning `/internal/verify`
       endpointida tekshiradi va servisga `X-User` / `X-User-Role` sarlavhalarini qo‘yadi.
       Mijoz yuborgan bu sarlavhalar gateway’da har doim ustidan yoziladi.
    4. Servis `require_role()` bilan rolni tekshiradi.

JWT imzo kaliti (`CRYSTAL_JWT_SECRET`) FAQAT auth-service’da bo‘ladi — boshqa servislar
token yarata olmaydi. Hammasi standart kutubxonada (hmac, hashlib), tashqi bog‘liqliksiz.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from .errors import ForbiddenError, UnauthorizedError

ADMIN = "admin"
OPERATOR = "operator"
COURIER = "courier"
ROLES = (ADMIN, OPERATOR, COURIER)

USER_HEADER = "X-User"
ROLE_HEADER = "X-User-Role"

PASSWORD_ITERATIONS = 310_000  # OWASP tavsiyasi: PBKDF2-HMAC-SHA256


# --- JWT -------------------------------------------------------------------------
def _b64encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def encode_jwt(claims, secret):
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = (
        _b64encode(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64encode(json.dumps(claims, separators=(",", ":"), ensure_ascii=False).encode())
    )
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return signing_input + "." + _b64encode(signature)


def decode_jwt(token, secret, issuer, now=None, leeway=30):
    """Imzo, `alg`, `iss`, `exp`, `nbf`ni tekshiradi. Xato bo‘lsa UnauthorizedError."""
    try:
        header_b64, claims_b64, signature_b64 = token.split(".")
        header = json.loads(_b64decode(header_b64))
        claims = json.loads(_b64decode(claims_b64))
        signature = _b64decode(signature_b64)
    except (ValueError, TypeError, UnicodeDecodeError):
        raise UnauthorizedError("Token noto‘g‘ri.")
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise UnauthorizedError("Token algoritmi qo‘llab-quvvatlanmaydi.")  # "alg": "none" hujumi
    expected = hmac.new(
        secret.encode(), (header_b64 + "." + claims_b64).encode(), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise UnauthorizedError("Token imzosi noto‘g‘ri.")
    if not isinstance(claims, dict):
        raise UnauthorizedError("Token noto‘g‘ri.")
    now = time.time() if now is None else now
    if claims.get("iss") != issuer:
        raise UnauthorizedError("Token boshqa manba tomonidan berilgan.")
    if not isinstance(claims.get("exp"), (int, float)) or now > claims["exp"] + leeway:
        raise UnauthorizedError("Token muddati tugagan.")
    if isinstance(claims.get("nbf"), (int, float)) and now + leeway < claims["nbf"]:
        raise UnauthorizedError("Token hali amal qilmaydi.")
    if claims.get("role") not in ROLES or not claims.get("sub"):
        raise UnauthorizedError("Token noto‘g‘ri.")
    return claims


def bearer_token(headers):
    value = headers.get("Authorization") or ""
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Avtorizatsiya kerak: Authorization: Bearer <token>.")
    return token.strip()


# --- parollar --------------------------------------------------------------------
def hash_password(password, iterations=PASSWORD_ITERATIONS):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password, stored):
    try:
        algorithm, iterations, salt, digest = stored.split("$")
        iterations = int(iterations)
    except (ValueError, AttributeError):
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64decode(salt), iterations)
    return hmac.compare_digest(candidate, _b64decode(digest))


def hash_token(token):
    """Refresh token bazada faqat xesh ko‘rinishida saqlanadi."""
    return hashlib.sha256(token.encode()).hexdigest()


# --- servislarda rol tekshiruvi ---------------------------------------------------
class Principal:
    def __init__(self, username, role):
        self.username = username
        self.role = role

    def __repr__(self):
        return f"Principal({self.username!r}, {self.role!r})"


def current_user(request):
    username = (request.headers.get(USER_HEADER) or "").strip()
    role = (request.headers.get(ROLE_HEADER) or "").strip()
    if not username or role not in ROLES:
        raise UnauthorizedError("Avtorizatsiya kerak: avval tizimga kiring.")
    return Principal(username, role)


def require_role(request, *roles):
    user = current_user(request)
    if user.role not in roles:
        raise ForbiddenError("Bu amal uchun ruxsat yo‘q.")
    return user
