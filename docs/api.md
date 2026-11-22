# API hujjati

Asosiy manzil: `http://localhost:8000` — **gateway** (nginx). Mijoz faqat gateway bilan ishlaydi; so‘rov qaysi servisga borishini gateway hal qiladi (har bir endpoint yonida ko‘rsatilgan). Har bir javobda `X-Request-ID` sarlavhasi bor — muammo bo‘lsa shu qiymat bilan loglardan izlang. Barcha javoblar `application/json; charset=utf-8`. Vaqtlar UTC, ISO-8601 (`2026-11-21T10:00:00+00:00`).

Buyurtma kodi katta-kichik harfga sezgir emas: `cry-abc…` va `CRY-ABC…` bir xil.

## Xato formati

```json
{"error": "Bu amal uchun buyurtma «Omborda» holatida bo‘lishi kerak."}
```

| Kod | Qachon |
| --- | --- |
| `400 Bad Request` | Bo‘sh manzil/kuryer, noma’lum ombor, noto‘g‘ri JSON, tana obyekt emas |
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
| `GET /health/order` · `/health/courier` · `/health/tracking` | tegishli servis |

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

Faqat `Omborda` holatida, bir marta. courier-service holatni order-service’dan so‘raydi; order-service ishlamasa `503`.

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

`Yo‘lda → Yetkazildi`. `order.status_changed` hodisasi orqali courier-service `delivered_at`ni yozadi.

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

---

## To‘liq ssenariy

```sh
BASE=http://localhost:8000
CODE=$(curl -s -X POST $BASE/api/v1/orders -H 'Content-Type: application/json' \
       -d '{"address":"Demo manzil"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["code"])')
curl -s -X POST $BASE/api/v1/orders/$CODE/receive
curl -s -X POST $BASE/api/v1/orders/$CODE/assign -H 'Content-Type: application/json' -d '{"courier":"Demo kuryer"}'
curl -s -X POST $BASE/api/v1/orders/$CODE/dispatch
curl -s -X POST $BASE/api/v1/orders/$CODE/deliver
curl -s $BASE/api/v1/orders/$CODE
sleep 1; curl -s $BASE/api/v1/tracking/$CODE
```

Bu ssenariy avtomatlashtirilgan holda: `./scripts/smoke_test.sh`.
