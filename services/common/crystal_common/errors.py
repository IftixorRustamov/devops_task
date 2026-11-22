"""Barcha servislar uchun umumiy xato turlari va ularning HTTP kodlari."""


class DomainError(Exception):
    """Barcha biznes xatolarining asosi."""

    status = 500


class ValidationError(DomainError):
    """Kiritilgan ma’lumot noto‘g‘ri."""

    status = 400


class NotFoundError(DomainError):
    """Obyekt topilmadi."""

    status = 404


class ConflictError(DomainError):
    """Amal joriy holatda bajarilmaydi."""

    status = 409


class UpstreamError(DomainError):
    """Boshqa servis javob bermadi yoki kutilmagan javob qaytardi."""

    status = 503


def require_text(value, message, max_length=200):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(message)
    value = value.strip()
    if len(value) > max_length:
        raise ValidationError(f"Matn {max_length} belgidan oshmasligi kerak.")
    return value


def normalize_code(code):
    return (code or "").strip().upper()
