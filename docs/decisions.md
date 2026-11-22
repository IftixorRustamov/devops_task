# Texnik qarorlar

## 2026-11-08. Python va SQLite

Prototip Python 3.9+ standart kutubxonasidan foydalanadi. SQLite alohida server o‘rnatmasdan lokal buyurtmalarni saqlaydi. Demo xotiradagi ma’lumotlar bazasida ishlaydi.

## 2026-11-08. Holat tarixi

Har bir holat o‘zgarishi tarixga qo‘shiladi. Joriy holat oxirgi yozuvdan olinadi. Tizim bosqichlarni tartib bilan bajarishni talab qiladi. Kuzatuv natijasida manzil va kuryer nomi chiqarilmaydi.

## 2026-11-21. Qatlamli tuzilma va REST API

`app.py` bitta fayldan `crystal/` paketiga ajratildi: `domain` (qoidalar), `repository` (SQL), `service` (hayot sikli), `api` va `cli` (kirish nuqtalari). HTTP API ham, CLI ham bitta `OrderService`ni chaqiradi — qoida bir joyda yoziladi. `python3 app.py …` buyruqlari orqaga moslik uchun saqlandi.

API standart kutubxonadagi `http.server` (`ThreadingHTTPServer`) asosida. Sabab: tashqi bog‘liqlik yo‘q, obrazda `pip install` bosqichi kerak emas, jamoaning “standart kutubxona” qarori saqlanadi. Loyiha o‘sganda FastAPI’ga o‘tish faqat `api/` qatlamini o‘zgartiradi.

Xatolar domen turlariga ajratildi: `ValidationError` → 400, `NotFoundError` → 404, `ConflictError` → 409.

## 2026-11-21. Docker va ma’lumot saqlash

Dockerfile ikki bosqichli: `test` bosqichi testlarni obraz ichida ishlatadi, `runtime` bosqichi faqat ilova kodini oladi. Konteyner root bo‘lmagan foydalanuvchi bilan, faqat o‘qiladigan fayl tizimida ishlaydi.

SQLite saqlanib qoldi, baza `/data` Docker volume’ida. Sabab: bitta konteyner uchun alohida DB server ortiqcha murakkablik. Bir nechta replika kerak bo‘lganda PostgreSQL’ga o‘tiladi. Parallel yozishlar `BEGIN IMMEDIATE` va `WAL` rejimi bilan xavfsiz.

## 2026-11-22. Mikroservislar va database-per-service

Monolit (`crystal/`) uchta servisga ajratildi: `order-service` (buyurtma va holat mashinasi),
`courier-service` (kuryer biriktirish), `tracking-service` (ommaviy kuzatuv, read model).
Chegaralar biznes sohasi bo‘yicha: har bir servis o‘z ma’lumotining yagona egasi.

**Har bir servisning o‘z PostgreSQL serveri.** Alohida foydalanuvchi, parol, volume va yopiq
tarmoq. Servislar boshqa servis jadvaliga murojaat qilmaydi — faqat API yoki hodisa orqali.
Bitta PostgreSQL ichida uchta baza ham mumkin edi (resurs tejaladi), lekin alohida serverlar
izolyatsiyani tarmoq darajasida ko‘rsatadi va servislarni alohida masshtablash/zaxiralashga
imkon beradi. SQLite endi faqat testlarda: bir nechta replika va tarmoq orqali ulanish kerak.

**Aloqa: HTTP + RabbitMQ.** Javob darhol kerak bo‘lgan ikki tekshiruv sinxron HTTP
(`assign` → order holati, `dispatch` → kuryer bormi). Qolgan hamma narsa — hodisalar
(`order.created`, `order.status_changed`, `courier.assigned`) RabbitMQ topic exchange orqali.
Kafka ham ko‘rib chiqildi: hodisalar oqimi kichik, RabbitMQ’ni ishga tushirish va kuzatish
oddiyroq, DLQ tayyor mavjud.

**Transactional outbox + idempotent inbox.** Bazaga yozish va xabar yuborish bitta
tranzaksiyada bo‘lmaydi, shuning uchun hodisa avval o‘z bazasidagi `outbox`ga yoziladi, keyin
fon oqimi yuboradi. Natija: at-least-once yetkazish; qabul qiluvchi `processed_events` bilan
takrorni tashlab yuboradi. Broker o‘chib tursa ham yozish amallari ishlaydi (CI’da tekshiriladi).

**Gateway: nginx.** Yagona kirish nuqtasi, marshrutlash, `/internal/*`ni yopish, rate limit,
`X-Request-ID`. Kod yozish shart emas va root bo‘lmagan obraz mavjud.

**Bog‘liqliklar.** “Faqat standart kutubxona” qarori o‘zgardi: konteynerlarda `psycopg` va
`pika` (versiyalari qat’iy belgilangan, `services/requirements.txt`). Testlar esa avvalgidek
tashqi kutubxonasiz ishlaydi — baza adapteri SQLite’ni, shina esa xotiradagi variantni qo‘llaydi.
HTTP server hamon `http.server`; FastAPI’ga o‘tish faqat `crystal_common.http`ni o‘zgartiradi.

**Kelishuv (trade-off).** `tracking-service` bir necha yuz millisekund orqada qolishi mumkin
(eventual consistency); eng so‘nggi holat uchun `GET /api/v1/orders/{code}` (order-service).
`dispatch` courier-service ishlamasa bajarilmaydi (`503`) — bu ongli tanlov: kuryersiz
yuborishdan ko‘ra kutgan afzal.

**Orqaga moslik.** Tashqi API yo‘llari o‘zgarmadi (gateway `:8000`), faqat
`GET /api/v1/tracking/{code}` va `/health/<servis>` qo‘shildi. Eski CLI (`app.py`) olib
tashlandi — u bazaga to‘g‘ridan-to‘g‘ri yozardi, bu esa database-per-service qoidasini buzadi.
