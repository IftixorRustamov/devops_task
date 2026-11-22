"""order-service: omborlar, buyurtmalar va buyurtma holat mashinasi.

Egasi bo‘lgan baza: order-db (warehouses, orders, order_events, outbox).
Chiqaradigan hodisalar: order.created, order.status_changed.
Sinxron bog‘liqlik: courier-service (dispatch oldidan kuryer biriktirilganini tekshirish).
"""
