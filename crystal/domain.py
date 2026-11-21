"""Domen qoidalari: holatlar, o‘tishlar va xatolar. Bu modul bazaga ham, HTTP’ga ham bog‘liq emas."""

NEW = "Yangi"
IN_WAREHOUSE = "Omborda"
IN_TRANSIT = "Yo‘lda"
DELIVERED = "Yetkazildi"

STATUSES = (NEW, IN_WAREHOUSE, IN_TRANSIT, DELIVERED)

# amal -> (talab qilinadigan joriy holat, keyingi holat)
TRANSITIONS = {
    "receive": (NEW, IN_WAREHOUSE),
    "dispatch": (IN_WAREHOUSE, IN_TRANSIT),
    "deliver": (IN_TRANSIT, DELIVERED),
}

CODE_PREFIX = "CRY-"


class DomainError(Exception):
    """Barcha biznes xatolarining asosi."""


class ValidationError(DomainError):
    """Kiritilgan ma’lumot noto‘g‘ri (HTTP 400)."""


class NotFoundError(DomainError):
    """Obyekt topilmadi (HTTP 404)."""


class ConflictError(DomainError):
    """Amal joriy holatda bajarilmaydi (HTTP 409)."""


def normalize_code(code):
    return (code or "").strip().upper()


def require_text(value, message):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(message)
    return value.strip()
