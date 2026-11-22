"""tracking-service: ommaviy kuzatuv (read model / CQRS).

Egasi bo‘lgan baza: tracking-db (shipments, timeline, processed_events).
Tinglaydigan hodisalar: order.*, courier.assigned. O‘zi hodisa chiqarmaydi.
Boshqa servislarga sinxron murojaat qilmaydi — ular ishlamasa ham kuzatuv ishlaydi.
"""
