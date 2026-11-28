# API hujjati

Asosiy manzil: `http://localhost:8000` — **gateway** (nginx). Mijoz faqat gateway bilan ishlaydi; so‘rov qaysi servisga borishini gateway hal qiladi (har bir endpoint yonida ko‘rsatilgan). Har bir javobda `X-Request-ID` sarlavhasi bor — muammo bo‘lsa shu qiymat bilan loglardan izlang. Barcha javoblar `application/json; charset=utf-8`. Vaqtlar UTC, ISO-8601 (`2026-11-21T10:00:00+00:00`).

Buyurtma kodi katta-kichik harfga sezgir emas: `cry-abc…` va `CRY-ABC…` bir xil.

## Autentifikatsiya

Ommaviy yo‘llardan (`/health*`, `/api/v1/auth/login|refresh|logout`, `/api/v1/tracking/*`)
tashqari HAR BIR so‘rov token talab qiladi:

```sh
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin_dev_password"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/auth/me
```

| Rol | Nima qila oladi |
| --- | --- |
| `admin` | Hammasi + foydalanuvchilarni boshqarish |
| `operator` | Buyurtma yaratish, qabul, biriktirish, yo‘lga chiqarish, topshirish |
| `courier` | O‘z buyurtmalari ro‘yxati, faqat O‘ZIGA biriktirilgan buyurtmani topshirish, buyurtma holatini ko‘rish |

`401` — token yo‘q, noto‘g‘ri yoki muddati o‘tgan. `403` — token to‘g‘ri, lekin rol mos emas.

### `POST /api/v1/auth/login` — auth-service

`{"username": "admin", "password": "..."}` → `200`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs…",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_token": "Qm9k…",
  "user": {"username": "admin", "role": "admin"}
}
```

Noto‘g‘ri login yoki parol — `401` (qaysi biri xato ekanini aytmaydi). IP bo‘yicha
daqiqasiga 60 ta urinish (gateway).

### `POST /api/v1/auth/refresh`

`{"refresh_token": "..."}` → yangi juftlik (login javobi kabi). Eski refresh token shu zahoti
bekor bo‘ladi. Bir marta ishlatilgan token qayta yuborilsa — `401` va foydalanuvchining
**barcha** refresh tokenlari bekor qilinadi (o‘g‘irlanganini aniqlash).

### `POST /api/v1/auth/logout`

`{"refresh_token": "..."}` → `{"logged_out": true}`.

### `GET /api/v1/auth/me`

`{"username": "ali", "role": "courier", "active": true}`

### Foydalanuvchilar (faqat admin)

| Metod | Yo‘l | Tana |
| --- | --- | --- |
| `GET` | `/api/v1/auth/users` | — |
| `POST` | `/api/v1/auth/users` | `{"username": "ali", "password": "kamida-8-belgi", "role": "courier"}` → `201` |
| `PATCH` | `/api/v1/auth/users/{username}` | `{"active": false}` — bloklash, refresh tokenlar bekor qilinadi |

Login: 3–32 belgi, kichik lotin harflari, raqam, `_ . -`. Parol: 8–128 belgi.

## Xato formati

```json
{"error": "Bu amal uchun buyurtma «Omborda» holatida bo‘lishi kerak."}
```

| Kod | Qachon |
| --- | --- |
| `400 Bad Request` | Bo‘sh manzil, noma’lum ombor yoki kuryer logini, noto‘g‘ri JSON, tana obyekt emas |
| `401 Unauthorized` | Token yo‘q, noto‘g‘ri yoki muddati o‘tgan; noto‘g‘ri login/parol |
| `403 Forbidden` | Rolga ruxsat yo‘q; kuryer boshqa kuryerning buyurtmasini topshirmoqchi |
| `404 Not Found` | Buyurtma yoki yo‘l topilmadi |
| `405 Method Not Allowed` | Yo‘l bor, lekin metod noto‘g‘ri |
| `409 Conflict` | Amal joriy holatda bajarilmaydi (bosqich o‘tkazib yuborilgan, kuryer allaqachon biriktirilgan) |
| `413 Payload Too Large` | Tana 64 KB dan katta |
| `429 Too Many Requests` | Gateway limiti (IP bo‘yicha 50 so‘rov/s) oshdi |
| `500 Internal Server Error` | Kutilmagan xato (tafsilot faqat server logida) |
| `503 Service Unavailable` | Kerakli servis yoki uning bog‘liqligi ishlamayapti (masalan, dispatch paytida courier-service) |

---

## Sog‘liq tekshiruvi

| Yo‘l | Javob beradi |
| --- | --- |
| `GET /health` | gateway o‘zi |
| `GET /health/auth` · `/health/order` · `/health/courier` · `/health/tracking` | tegishli servis |

```sh
curl localhost:8000/health/order
```
```json
{
  "status": "ok",
  "service": "order-service",
  "version": "2.0.0",
  "checks": {"database": "ok", "broker": "ok", "outbox_relay": "ok"}
}
```

`status`: `ok` — hammasi ishlaydi; `degraded` (`200`) — broker yo‘q, lekin servis ishlaydi va
hodisalar outbox’da kutadi; `fail` (`503`) — servisning bazasi ishlamayapti.

## `GET /api/v1/warehouses` — order-service

```json
{"items": [{"id": 1, "name": "Markaziy ombor"}]}
```

## `POST /api/v1/orders` — order-service

| Maydon | Turi | Majburiy | Izoh |
| --- | --- | --- | --- |
| `address` | string | ha | Bo‘sh bo‘lmasligi kerak, 500 belgigacha |
| `warehouse_id` | integer | yo‘q | Standart `1` |

```sh
curl -X POST localhost:8000/api/v1/orders \
     -H 'Content-Type: application/json' \
     -d '{"address": "Toshkent, Demo ko‘chasi 1"}'
```
`201 Created`
```json
{"code": "CRY-4F1A9C0D2B7E4A61B3C8", "status": "Yangi"}
```

## `GET /api/v1/orders/{code}` — order-service

Joriy holat va to‘liq tarix, order-service bazasidan (har doim eng so‘nggi holat). Manzil va kuryer nomi qaytarilmaydi.

`200 OK`
```json
{
  "code": "CRY-4F1A9C0D2B7E4A61B3C8",
  "status": "Yo‘lda",
  "history": [
    {"status": "Yangi", "created_at": "2026-11-21T10:00:00+00:00"},
    {"status": "Omborda", "created_at": "2026-11-21T10:05:12+00:00"},
    {"status": "Yo‘lda", "created_at": "2026-11-21T10:30:40+00:00"}
  ]
}
```

## `POST /api/v1/orders/{code}/receive` — order-service

`Yangi → Omborda`. Tana kerak emas.

```json
{"code": "CRY-…", "status": "Omborda"}
```

## `POST /api/v1/orders/{code}/assign` — courier-service

Faqat `Omborda` holatida, bir marta. `courier` — auth-service’dagi faol `courier` rolidagi login
(aks holda `400`). courier-service holatni order-service’dan, loginni auth-service’dan so‘raydi;
ular ishlamasa `503`.

```sh
curl -X POST localhost:8000/api/v1/orders/CRY-…/assign \
     -H 'Content-Type: application/json' -d '{"courier": "Demo kuryer"}'
```
```json
{"code": "CRY-…", "assigned": true}
```

## `POST /api/v1/orders/{code}/dispatch` — order-service

`Omborda → Yo‘lda`. Avval kuryer biriktirilgan bo‘lishi shart, aks holda `409`. order-service buni courier-service’dan so‘raydi; courier-service ishlamasa `503`.

## `POST /api/v1/orders/{code}/deliver` — order-service

`Yo‘lda → Yetkazildi`. Operator/admin yoki **shu buyurtmaga biriktirilgan** kuryer. Boshqa kuryer — `403`.
`order.status_changed` hodisasi orqali courier-service `delivered_at`ni yozadi.

## `GET /api/v1/couriers/me/assignments` — courier-service

Faqat `courier` roli. `{"items": [{"code": "CRY-…", "assigned_at": "…", "delivered_at": null}]}`

## `GET /api/v1/tracking/{code}` — tracking-service

Ommaviy kuzatuv. Hodisalardan quriladi, shuning uchun amaldan keyin **bir necha yuz millisekund**
kechikishi mumkin (eventual consistency). Hodisa hali yetib kelmagan bo‘lsa — `404`.
Manzil ham, kuryer nomi ham qaytarilmaydi.

`200 OK`
```json
{
  "code": "CRY-4F1A9C0D2B7E4A61B3C8",
  "status": "Yo‘lda",
  "courier_assigned": true,
  "updated_at": "2026-11-22T10:30:40.123456+00:00",
  "timeline": [
    {"event": "order.created", "status": "Yangi", "at": "2026-11-22T10:00:00.120000+00:00"},
    {"event": "order.status_changed", "status": "Omborda", "at": "2026-11-22T10:05:12.410000+00:00"},
    {"event": "courier.assigned", "status": null, "at": "2026-11-22T10:20:03.900000+00:00"},
    {"event": "order.status_changed", "status": "Yo‘lda", "at": "2026-11-22T10:30:40.123456+00:00"}
  ]
}
```

## Ichki endpointlar (gateway orqali yopiq)

Faqat servislar o‘rtasida, `backend` tarmog‘ida. Gateway `/internal/*` uchun `404` qaytaradi.

| Servis | Yo‘l | Kim chaqiradi |
| --- | --- | --- |
| order-service | `GET /internal/orders/{code}` → `code`, `status`, `warehouse_id`, `version` | courier-service |
| courier-service | `GET /internal/assignments/{code}` → `courier`, `assigned_at`, `delivered_at` | order-service |
| auth-service | `GET /internal/verify` — `Authorization` tekshiruvi, javobda `X-User`, `X-User-Role` | gateway |
| auth-service | `GET /internal/users/{username}` → `role`, `active` | courier-service |

---

## To‘liq ssenariy

```sh
BASE=http://localhost:8000
login() { curl -s -X POST $BASE/api/v1/auth/login -H 'Content-Type: application/json' \
  -d "{\"username\":\"$1\",\"password\":\"$2\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])'; }
ADMIN=$(login admin admin_dev_password)
for u in "op1 operator" "ali courier"; do set -- $u
  curl -s -X POST $BASE/api/v1/auth/users -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
       -d "{\"username\":\"$1\",\"password\":\"demo-parol-1\",\"role\":\"$2\"}"; done
OP=$(login op1 demo-parol-1); ALI=$(login ali demo-parol-1)
auth() { echo "Authorization: Bearer $1"; }
CODE=$(curl -s -X POST $BASE/api/v1/orders -H "$(auth $OP)" -H 'Content-Type: application/json' \
       -d '{"address":"Demo manzil"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["code"])')
curl -s -X POST $BASE/api/v1/orders/$CODE/receive  -H "$(auth $OP)"
curl -s -X POST $BASE/api/v1/orders/$CODE/assign   -H "$(auth $OP)" -H 'Content-Type: application/json' -d '{"courier":"ali"}'
curl -s -X POST $BASE/api/v1/orders/$CODE/dispatch -H "$(auth $OP)"
curl -s -X POST $BASE/api/v1/orders/$CODE/deliver  -H "$(auth $ALI)"     # kuryerning o‘zi topshiradi
sleep 1; curl -s $BASE/api/v1/tracking/$CODE                              # ommaviy, tokensiz
```

Avtomatlashtirilgan va kengroq variant: `./scripts/smoke_test.sh`. Brauzerda: `http://localhost:8000/`.
