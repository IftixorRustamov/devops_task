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
