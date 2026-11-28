# Crystal Logistics

PDP University Unit 4 DevOps. Crystal jamoasi, 2-variant. Logistika va kuryer xizmati.

Buyurtmani yaratish, omborga qabul qilish, kuryerga biriktirish, yo‘lga chiqarish va topshirishni
kuzatadigan tizim. **Mikroservis arxitekturasi**: to‘rtta mustaqil servis, har birining **o‘z
PostgreSQL bazasi**, ular o‘rtasida RabbitMQ hodisalari, bitta API gateway va **JWT bilan
rollarga asoslangan kirish**.

> **Docker’siz ko‘rsatish:** GitHub → **Code → Codespaces → Create codespace on main**.
> Stack o‘zi ko‘tariladi va brauzerda namoyish sahifasi ochiladi. Batafsil: [docs/demo.md](docs/demo.md).

```
               ┌──────────── gateway (nginx) :8000 — JWT tekshiruvi ────────────┐
               │                  │                    │                         │
         auth-service      order-service  ◄─HTTP─►  courier-service      tracking-service
               │                  │                    │                         │
            auth-db           order-db             courier-db              tracking-db
                                  └──── hodisalar ──► RabbitMQ ──► hodisalar ────┘
```

| Servis | Vazifa | Baza |
| --- | --- | --- |
| `auth-service` | Foydalanuvchilar, rollar, JWT va refresh tokenlar | `auth-db` |
| `order-service` | Omborlar, buyurtmalar, holat mashinasi | `order-db` |
| `courier-service` | Kuryer biriktirish | `courier-db` |
| `tracking-service` | Ommaviy kuzatuv (hodisalardan quriladi) | `tracking-db` |
| `gateway` | Yagona kirish, token tekshiruvi, marshrutlash, rate limit, namoyish sahifasi | — |

## Tez ishga tushirish

Talab: Docker 24+ va Docker Compose v2.24+, ~1.5 GB bo‘sh RAM.

```sh
cp .env.example .env                      # parollar (lokal uchun shundayicha ham bo‘ladi)
docker compose up --build --detach --wait --wait-timeout 180
curl http://localhost:8000/health/order
open http://localhost:8000                # namoyish sahifasi (admin / admin_dev_password)
./scripts/smoke_test.sh                   # to‘liq hayot sikli gateway orqali
./scripts/resilience_test.sh              # izolyatsiya, broker o‘chishi, restart
```

RabbitMQ paneli: <http://localhost:15672>. To‘xtatish: `docker compose down` (ma’lumotlar
saqlanadi). Hammasini o‘chirish: `docker compose down --volumes`. `make help` — barcha qisqa buyruqlar.

## API qisqacha

Token olish: `POST /api/v1/auth/login {"username","password"}` → `access_token`; keyin har bir
so‘rovda `Authorization: Bearer <token>`.

| Metod | Yo‘l | Servis | Kim |
| --- | --- | --- | --- |
| `GET` | `/health`, `/health/{auth,order,courier,tracking}` | gateway / servis | hamma |
| `POST` | `/api/v1/auth/login` · `/refresh` · `/logout` | auth | hamma |
| `GET` | `/api/v1/auth/me` | auth | tizimga kirgan |
| `GET` `POST` `PATCH` | `/api/v1/auth/users[/{username}]` | auth | admin |
| `GET` | `/api/v1/warehouses` | order | admin, operator |
| `POST` | `/api/v1/orders` `{"recipient_name", "recipient_phone", "address"}` | order | admin, operator |
| `GET` | `/api/v1/orders?q=&status=&limit=&offset=` | order | admin, operator |
| `POST` | `/api/v1/orders/{code}/cancel` `{"reason"}` | order | admin, operator |
| `GET` | `/api/v1/orders/{code}` | order | admin, operator, biriktirilgan kuryer |
| `POST` | `/api/v1/orders/{code}/receive` · `/dispatch` | order | admin, operator |
| `POST` | `/api/v1/orders/{code}/assign` `{"courier": "<login>"}` | courier | admin, operator |
| `POST` | `/api/v1/orders/{code}/deliver` | order | admin, operator, **biriktirilgan** kuryer |
| `GET` | `/api/v1/couriers/me/assignments` | courier | kuryer |
| `GET` | `/api/v1/stats` · `/api/v1/couriers/stats` | order · courier | admin, operator (dashboard) |
| `GET` | `/api/v1/tracking/{code}` | tracking | hamma (manzil va kuryer nomisiz) |

Holatlar: `Yangi → Omborda → Yo‘lda → Yetkazildi`, yoki `Bekor qilindi` (faqat yo‘lga chiqmasdan oldin). Bosqichni o‘tkazib yuborish yoki ortga qaytish mumkin emas (`409`). To‘liq tavsif: [docs/api.md](docs/api.md).

## Muhim kafolatlar

- **JWT + rollar** — gateway har so‘rovni tekshiradi (standart holatda hamma yo‘l yopiq), imzo kaliti faqat auth-service’da; refresh token bir martalik, qayta ishlatilsa barcha sessiyalar bekor qilinadi.
- **Database-per-service** — har bir baza alohida yopiq tarmoqda; boshqa servis unga ulana olmaydi.
- **Transactional outbox** — RabbitMQ o‘chib tursa ham buyurtmalar yaratiladi, hodisalar keyin yetib boradi.
- **Idempotent consumer’lar** va **dead letter queue** — takroriy yoki buzuq xabar tizimni buzmaydi.
- **Circuit breaker va timeout** — bitta servis osilib qolsa, boshqasi ham osilmaydi (`503`).
- **JSON loglar + `X-Request-ID`** — bitta so‘rovning barcha servislardagi izi.

Bularning hammasi CI’da haqiqiy PostgreSQL va RabbitMQ bilan tekshiriladi.

## Loyiha tuzilmasi

```
services/
  common/crystal_common/   umumiy: baza adapteri, HTTP, RabbitMQ, outbox/inbox, JWT, loglar
  auth/auth_service/       foydalanuvchilar, login, tokenlar
  order/order_service/     domain, schema, service, api
  courier/courier_service/
  tracking/tracking_service/
  requirements.txt         psycopg, pika (faqat konteynerda)
gateway/nginx.conf         marshrutlash va token tekshiruvi
gateway/demo/index.html    namoyish sahifasi
.devcontainer/             GitHub Codespaces sozlamasi
tests/                     unit + 3 servisli integratsion testlar
scripts/                   smoke_test.sh, resilience_test.sh
Dockerfile                 deps → test → runtime (SERVICE build argumenti)
compose.yaml               10 konteyner, 7 tarmoq, 5 volume
```

## Testlar

```sh
python3 -m unittest discover -s tests -v    # Python 3.9+, tashqi kutubxonasiz
docker build --target test .                # Docker ichida
```

Lokal testlar SQLite va xotiradagi shinani ishlatadi — to‘rtta servis haqiqiy HTTP orqali, har biri
o‘z bazasi bilan ishga tushadi. GitHub Actions har bir `main` PR’ida bundan tashqari butun
stack’ni ko‘tarib smoke va resilience testlarini ishlatadi.

## Hujjatlar

- [Namoyish](docs/demo.md) — Codespaces’da ishga tushirish va o‘qituvchiga ko‘rsatish ssenariysi
- [Mahsulot](docs/product.md) — foydalanuvchilar, muammolar, ustuvorlik, roadmap
- [Interfeys dizayni](docs/design.md) — ranglar, tugmalar, maket va ularning sabablari
- [Arxitektura](docs/architecture.md) — servislar, bazalar, hodisalar, autentifikatsiya, kafolatlar
- [API](docs/api.md) — endpointlar, misollar, xatolar
- [Docker va deploy](docs/deployment.md) — konteynerlar, tarmoqlar, sozlamalar, backup, nosozliklar
- [Qarorlar](docs/decisions.md) · [Jamoa kelishuvi](docs/team-charter.md) · [Kirish huquqlari](docs/access.md) · [Stand-up](docs/meetings.md)
