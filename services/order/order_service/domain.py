"""Buyurtma holatlari va o‘tishlar. Bazaga ham, HTTP’ga ham bog‘liq emas."""

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

ORDER_CREATED = "order.created"
ORDER_STATUS_CHANGED = "order.status_changed"
