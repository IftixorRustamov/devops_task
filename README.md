# Crystal Logistics

PDP University Unit 4 DevOps. Crystal jamoasi, 2-variant. Logistika va kuryer xizmati.

Buyurtmani yaratish, omborga qabul qilish, kuryerga biriktirish, yo‘lga chiqarish va topshirishni
kuzatadigan tizim. **Mikroservis arxitekturasi**: uchta mustaqil servis, har birining **o‘z
PostgreSQL bazasi**, ular o‘rtasida RabbitMQ hodisalari va bitta API gateway.

```
            ┌──────────── gateway (nginx) :8000 ────────────┐
            │                    │                          │
      order-service  ◄─HTTP─►  courier-service       tracking-service
            │                    │                          │
        order-db             courier-db               tracking-db
            └───── hodisalar ──► RabbitMQ ──► hodisalar ────┘
```

| Servis | Vazifa | Baza |
| --- | --- | --- |
| `order-service` | Omborlar, buyurtmalar, holat mashinasi | `order-db` |
| `courier-service` | Kuryer biriktirish | `courier-db` |
| `tracking-service` | Ommaviy kuzatuv (hodisalardan quriladi) | `tracking-db` |
| `gateway` | Yagona kirish, marshrutlash, rate limit, `X-Request-ID` | — |

## Tez ishga tushirish

Talab: Docker 24+ va Docker Compose v2.24+, ~1.5 GB bo‘sh RAM.

```sh
cp .env.example .env                      # parollar (lokal uchun shundayicha ham bo‘ladi)
docker compose up --build --detach --wait --wait-timeout 180
curl http://localhost:8000/health/order
./scripts/smoke_test.sh                   # to‘liq hayot sikli gateway orqali
./scripts/resilience_test.sh              # izolyatsiya, broker o‘chishi, restart
```

RabbitMQ paneli: <http://localhost:15672>. To‘xtatish: `docker compose down` (ma’lumotlar
saqlanadi). Hammasini o‘chirish: `docker compose down --volumes`. `make help` — barcha qisqa buyruqlar.

## API qisqacha

| Metod | Yo‘l | Servis | Vazifa |
| --- | --- | --- | --- |
| `GET` | `/health`, `/health/{order,courier,tracking}` | gateway / servis | Holat |
| `GET` | `/api/v1/warehouses` | order | Omborlar ro‘yxati |
| `POST` | `/api/v1/orders` | order | Buyurtma yaratish `{"address": "...", "warehouse_id": 1}` |
| `GET` | `/api/v1/orders/{code}` | order | Joriy holat va tarix |
| `POST` | `/api/v1/orders/{code}/receive` | order | Omborga qabul qilish |
| `POST` | `/api/v1/orders/{code}/assign` | courier | Kuryer biriktirish `{"courier": "..."}` |
| `POST` | `/api/v1/orders/{code}/dispatch` | order | Yo‘lga chiqarish (kuryer majburiy) |
| `POST` | `/api/v1/orders/{code}/deliver` | order | Topshirish |
| `GET` | `/api/v1/tracking/{code}` | tracking | Ommaviy kuzatuv (manzil va kuryer nomisiz) |

Holatlar: `Yangi → Omborda → Yo‘lda → Yetkazildi`. Bosqichni o‘tkazib yuborish yoki ortga
qaytish mumkin emas (`409`). To‘liq tavsif: [docs/api.md](docs/api.md).

## Muhim kafolatlar

- **Database-per-service** — har bir baza alohida yopiq tarmoqda; boshqa servis unga ulana olmaydi.
- **Transactional outbox** — RabbitMQ o‘chib tursa ham buyurtmalar yaratiladi, hodisalar keyin yetib boradi.
- **Idempotent consumer’lar** va **dead letter queue** — takroriy yoki buzuq xabar tizimni buzmaydi.
- **Circuit breaker va timeout** — bitta servis osilib qolsa, boshqasi ham osilmaydi (`503`).
- **JSON loglar + `X-Request-ID`** — bitta so‘rovning barcha servislardagi izi.

Bularning hammasi CI’da haqiqiy PostgreSQL va RabbitMQ bilan tekshiriladi.

## Loyiha tuzilmasi

```
services/
  common/crystal_common/   umumiy: baza adapteri, HTTP, RabbitMQ, outbox/inbox, loglar
  order/order_service/     domain, schema, service, api
  courier/courier_service/
  tracking/tracking_service/
  requirements.txt         psycopg, pika (faqat konteynerda)
gateway/nginx.conf         marshrutlash
tests/                     unit + 3 servisli integratsion testlar
scripts/                   smoke_test.sh, resilience_test.sh
Dockerfile                 deps → test → runtime (SERVICE build argumenti)
compose.yaml               8 konteyner, 6 tarmoq, 4 volume
```

## Testlar

```sh
python3 -m unittest discover -s tests -v    # Python 3.9+, tashqi kutubxonasiz
docker build --target test .                # Docker ichida
```

Lokal testlar SQLite va xotiradagi shinani ishlatadi — uchta servis haqiqiy HTTP orqali, har biri
o‘z bazasi bilan ishga tushadi. GitHub Actions har bir `main` PR’ida bundan tashqari butun
stack’ni ko‘tarib smoke va resilience testlarini ishlatadi.

## Hujjatlar

- [Arxitektura](docs/architecture.md) — servislar, bazalar, hodisalar, kafolatlar
- [API](docs/api.md) — endpointlar, misollar, xatolar
- [Docker va deploy](docs/deployment.md) — konteynerlar, tarmoqlar, sozlamalar, backup, nosozliklar
- [Qarorlar](docs/decisions.md) · [Jamoa kelishuvi](docs/team-charter.md) · [Kirish huquqlari](docs/access.md) · [Stand-up](docs/meetings.md)
