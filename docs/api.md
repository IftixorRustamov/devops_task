# API hujjati

Asosiy manzil: `http://localhost:8000`. Barcha javoblar `application/json; charset=utf-8`. Vaqtlar UTC, ISO-8601 (`2026-11-21T10:00:00+00:00`).

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
| `500 Internal Server Error` | Kutilmagan xato (tafsilot faqat server logida) |

---

## `GET /health`

Servis va bazaga ulanishni tekshiradi. Docker healthcheck shu endpointni ishlatadi.

```sh
curl localhost:8000/health
```
```json
{"status": "ok", "version": "1.0.0"}
```

## `GET /api/v1/warehouses`

```json
{"items": [{"id": 1, "name": "Markaziy ombor"}]}
```

## `POST /api/v1/orders`

| Maydon | Turi | Majburiy | Izoh |
| --- | --- | --- | --- |
| `address` | string | ha | Bo‘sh bo‘lmasligi kerak |
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

## `GET /api/v1/orders/{code}`

Joriy holat va to‘liq tarix. Manzil va kuryer nomi qaytarilmaydi.

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

## `POST /api/v1/orders/{code}/receive`

`Yangi → Omborda`. Tana kerak emas.

```json
{"code": "CRY-…", "status": "Omborda"}
```

## `POST /api/v1/orders/{code}/assign`

Faqat `Omborda` holatida, bir marta.

```sh
curl -X POST localhost:8000/api/v1/orders/CRY-…/assign \
     -H 'Content-Type: application/json' -d '{"courier": "Demo kuryer"}'
```
```json
{"code": "CRY-…", "assigned": true}
```

## `POST /api/v1/orders/{code}/dispatch`

`Omborda → Yo‘lda`. Avval kuryer biriktirilgan bo‘lishi shart, aks holda `409`.

## `POST /api/v1/orders/{code}/deliver`

`Yo‘lda → Yetkazildi`. `deliveries.delivered_at` ham yoziladi.

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
```

Bu ssenariy avtomatlashtirilgan holda: `./scripts/smoke_test.sh`.
