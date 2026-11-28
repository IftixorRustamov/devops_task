"""Foydalanuvchilar, login, refresh token rotatsiyasi va tokenni tekshirish."""

import logging
import re
import secrets
import time
from uuid import uuid4

from crystal_common.errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from crystal_common.events import utc_now
from crystal_common.security import (
    ADMIN, PASSWORD_ITERATIONS, ROLE_HEADER, ROLES, USER_HEADER,
    bearer_token, decode_jwt, encode_jwt, hash_password, hash_token, verify_password,
)

log = logging.getLogger("crystal.auth")

ISSUER = "crystal-auth"
USERNAME_RE = re.compile(r"[a-z0-9_.-]{3,32}")
MIN_PASSWORD = 8
LOGIN_FAILED = "Login yoki parol noto‘g‘ri."


class AuthService:
    def __init__(self, db, secret, access_ttl=900, refresh_ttl=7 * 24 * 3600,
                 password_iterations=PASSWORD_ITERATIONS, clock=time.time):
        if len(secret) < 32:
            raise ValueError("CRYSTAL_JWT_SECRET kamida 32 belgi bo‘lishi kerak.")
        self.db = db
        self.secret = secret
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        self.iterations = password_iterations
        self.clock = clock
        # Mavjud bo‘lmagan login uchun ham xesh hisoblanadi — javob vaqti login borligini oshkor qilmaydi.
        self._dummy_hash = hash_password(secrets.token_hex(8), password_iterations)

    # --- foydalanuvchilar -----------------------------------------------------
    def _validate(self, username, password, role):
        if not isinstance(username, str) or not USERNAME_RE.fullmatch(username.strip().lower()):
            raise ValidationError("Login 3–32 belgi: kichik lotin harflari, raqam, _ . -")
        if not isinstance(password, str) or len(password) < MIN_PASSWORD:
            raise ValidationError(f"Parol kamida {MIN_PASSWORD} belgi bo‘lishi kerak.")
        if len(password) > 128:
            raise ValidationError("Parol 128 belgidan oshmasligi kerak.")
        if role not in ROLES:
            raise ValidationError(f"Rol quyidagilardan biri bo‘lishi kerak: {', '.join(ROLES)}.")
        return username.strip().lower()

    def create_user(self, username, password, role):
        username = self._validate(username, password, role)
        password_hash = hash_password(password, self.iterations)
        with self.db.session(write=True) as session:
            cursor = session.execute(
                "INSERT INTO users (username, password_hash, role, active, created_at) "
                "VALUES (?, ?, ?, 1, ?) ON CONFLICT (username) DO NOTHING",
                (username, password_hash, role, utc_now()),
            )
            if cursor.rowcount == 0:
                raise ConflictError("Bunday login allaqachon mavjud.")
        log.info("Foydalanuvchi yaratildi: %s (%s)", username, role)
        return {"username": username, "role": role, "active": True}

    def ensure_admin(self, username, password):
        """Ishga tushishda birinchi admin’ni yaratadi (agar hali yo‘q bo‘lsa)."""
        try:
            self.create_user(username, password, ADMIN)
        except ConflictError:
            pass

    def list_users(self):
        with self.db.session() as session:
            rows = session.all("SELECT username, role, active, created_at FROM users ORDER BY username")
        return [{"username": u, "role": r, "active": bool(a), "created_at": c} for u, r, a, c in rows]

    def get_user(self, username):
        username = (username or "").strip().lower()
        with self.db.session() as session:
            row = session.one("SELECT role, active FROM users WHERE username = ?", (username,))
        if row is None:
            raise NotFoundError("Foydalanuvchi topilmadi.")
        return {"username": username, "role": row[0], "active": bool(row[1])}

    def set_active(self, username, active):
        if not isinstance(active, bool):
            raise ValidationError("active true yoki false bo‘lishi kerak.")
        username = (username or "").strip().lower()
        with self.db.session(write=True) as session:
            cursor = session.execute("UPDATE users SET active = ? WHERE username = ?", (int(active), username))
            if cursor.rowcount == 0:
                raise NotFoundError("Foydalanuvchi topilmadi.")
            if not active:
                self._revoke_all(session, username)
        return self.get_user(username)

    # --- tokenlar -------------------------------------------------------------
    def _issue(self, session, username, role):
        now = int(self.clock())
        access = encode_jwt({
            "iss": ISSUER, "sub": username, "role": role,
            "iat": now, "nbf": now, "exp": now + self.access_ttl, "jti": uuid4().hex,
        }, self.secret)
        refresh = secrets.token_urlsafe(32)
        token_id = uuid4().hex
        session.execute(
            "INSERT INTO refresh_tokens (id, username, token_hash, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (token_id, username, hash_token(refresh), now + self.refresh_ttl, utc_now()),
        )
        return token_id, {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": self.access_ttl,
            "refresh_token": refresh,
            "user": {"username": username, "role": role},
        }

    def _revoke_all(self, session, username):
        session.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE username = ? AND revoked_at IS NULL",
            (utc_now(), username),
        )

    def login(self, username, password):
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValidationError("username va password kerak.")
        username = username.strip().lower()
        with self.db.session(write=True) as session:
            row = session.one("SELECT password_hash, role, active FROM users WHERE username = ?", (username,))
            stored = row[0] if row else self._dummy_hash
            if not verify_password(password, stored) or row is None or not row[2]:
                log.warning("Muvaffaqiyatsiz login: %s", username[:32])
                raise UnauthorizedError(LOGIN_FAILED)
            _token_id, tokens = self._issue(session, username, row[1])
        return tokens

    def refresh(self, token):
        if not isinstance(token, str) or not token:
            raise ValidationError("refresh_token kerak.")
        now = int(self.clock())
        with self.db.session(write=True) as session:
            row = session.one(
                "SELECT t.id, t.username, t.expires_at, t.revoked_at, u.role, u.active "
                "FROM refresh_tokens t JOIN users u ON u.username = t.username "
                "WHERE t.token_hash = ?" + self.db.for_update,
                (hash_token(token),),
            )
            if row is None:
                raise UnauthorizedError("Refresh token noto‘g‘ri.")
            token_id, username, expires_at, revoked_at, role, active = row
            if revoked_at is not None:
                # Bir marta ishlatilgan token qayta keldi — u o‘g‘irlangan bo‘lishi mumkin.
                self._revoke_all(session, username)
                log.warning("Refresh token qayta ishlatildi, %s ning barcha sessiyalari bekor qilindi", username)
                revoked = True
            else:
                revoked = False
            if not revoked:
                if expires_at < now or not active:
                    raise UnauthorizedError("Refresh token muddati tugagan.")
                new_id, tokens = self._issue(session, username, role)
                session.execute(
                    "UPDATE refresh_tokens SET revoked_at = ?, replaced_by = ? WHERE id = ?",
                    (utc_now(), new_id, token_id),
                )
                return tokens
        # Tranzaksiya commit bo‘lgach (bekor qilish saqlansin) xato qaytariladi.
        raise UnauthorizedError("Refresh token allaqachon ishlatilgan. Qayta kiring.")

    def logout(self, token):
        if isinstance(token, str) and token:
            with self.db.session(write=True) as session:
                session.execute(
                    "UPDATE refresh_tokens SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                    (utc_now(), hash_token(token)),
                )
        return {"logged_out": True}

    def verify(self, headers):
        """Gateway uchun: access tokenni tekshirib, foydalanuvchi sarlavhalarini qaytaradi."""
        claims = decode_jwt(bearer_token(headers), self.secret, ISSUER, now=self.clock())
        return {"username": claims["sub"], "role": claims["role"]}, {
            USER_HEADER: claims["sub"], ROLE_HEADER: claims["role"],
        }
