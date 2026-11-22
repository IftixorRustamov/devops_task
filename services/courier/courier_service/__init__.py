"""courier-service: buyurtmalarni kuryerlarga biriktirish.

Egasi bo‘lgan baza: courier-db (assignments, outbox, processed_events).
Chiqaradigan hodisa: courier.assigned.
Tinglaydigan hodisa: order.status_changed (topshirilgan vaqtni yozish uchun).
Sinxron bog‘liqlik: order-service (biriktirishdan oldin buyurtma holatini tekshirish).
"""
