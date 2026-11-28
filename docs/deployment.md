# Docker va deploy

## Talablar

| Vosita | Versiya |
| --- | --- |
| Docker Engine | 24+ |
| Docker Compose | v2.24+ |
| Python (testlar va Docker’siz ishlatish) | 3.9+ |
| Bo‘sh RAM | ~2 GB (4 PostgreSQL + RabbitMQ + 4 servis + nginx) |

## Konteynerlar

| Konteyner | Obraz | Tarmoqlar | Volume | Hostga ochiq port |
| --- | --- | --- | --- | --- |
| `gateway` | `nginxinc/nginx-unprivileged:1.27-alpine` | edge, backend | — | `${CRYSTAL_PUBLISH_PORT:-8000}` |
| `auth-service` | `crystal-auth-service:local` | backend, auth-data | — | — |
| `order-service` | `crystal-order-service:local` | backend, events, order-data | — | — |
| `courier-service` | `crystal-courier-service:local` | backend, events, courier-data | — | — |
| `tracking-service` | `crystal-tracking-service:local` | backend, events, tracking-data | — | — |
| `auth-db` | `postgres:16-alpine` | auth-data | `auth-db-data` | — |
| `order-db` | `postgres:16-alpine` | order-data | `order-db-data` | — |
| `courier-db` | `postgres:16-alpine` | courier-data | `courier-db-data` | — |
| `tracking-db` | `postgres:16-alpine` | tracking-data | `tracking-db-data` | — |
| `rabbitmq` | `rabbitmq:3.13-management-alpine` | events, edge | `rabbitmq-data` | `127.0.0.1:15672` (panel) |

`edge`dan boshqa barcha tarmoqlar `internal: true` — internetga chiqmaydi va hostdan
to‘g‘ridan-to‘g‘ri ochilmaydi. Har bir `*-data` tarmog‘ida faqat bitta servis va uning bazasi bor.

Ishga tushish tartibi `depends_on: condition: service_healthy` bilan: bazalar va RabbitMQ →
servislar → gateway. Servis o‘zi ham bazani 60 s gacha kutadi (`CRYSTAL_STARTUP_TIMEOUT_S`).

## Dockerfile

Bitta Dockerfile to‘rtta servis obrazini yig‘adi; servisni `SERVICE` build argumenti tanlaydi.

| Bosqich | Vazifa |
| --- | --- |
| `deps` | `services/requirements.txt` (psycopg, pika) o‘rnatiladi |
| `test` | Barcha testlar obraz ichida. Test yiqilsa build to‘xtaydi |
| `runtime` | Faqat `crystal_common` va **shu servis** kodi. Testlar va boshqa servislar kodi kirmaydi |

```sh
docker build --target test -t crystal-logistics:test .
docker build --target runtime --build-arg SERVICE=order -t crystal-order-service .
```

Ishchi obraz: root emas (uid 10001), kod `root`ga tegishli, `HEALTHCHECK` `/health`ni
tekshiradi, `SIGTERM`da joriy so‘rovlar tugatilib, outbox relay va consumer’lar to‘xtatiladi.

## Ishga tushirish

```sh
cp .env.example .env                 # parollarni o‘zgartiring
docker compose up --build --detach --wait --wait-timeout 180
docker compose ps
./scripts/smoke_test.sh              # gateway orqali to‘liq ssenariy
./scripts/resilience_test.sh         # izolyatsiya, broker o‘chishi, restart
```

To‘xtatish: `docker compose down` (ma’lumot saqlanadi). Hammasini o‘chirish:
`docker compose down --volumes`.

Bitta servisni qayta yig‘ish: `docker compose up --build --detach --wait order-service`.

## Muhit o‘zgaruvchilari

Servislar (compose ularni o‘zi beradi):

| O‘zgaruvchi | Standart | Izoh |
| --- | --- | --- |
| `CRYSTAL_DATABASE_URL` | `sqlite:///<servis>.sqlite3` | Konteynerda `postgresql://…@<servis>-db:5432/<servis>` |
| `CRYSTAL_BROKER_URL` | bo‘sh → xotiradagi shina | Konteynerda `amqp://…@rabbitmq:5672/%2F` |
| `CRYSTAL_ORDER_SERVICE_URL` | `http://localhost:8001` | courier-service uchun |
| `CRYSTAL_COURIER_SERVICE_URL` | `http://localhost:8002` | order-service uchun |
| `CRYSTAL_PORT` | 8001 / 8002 / 8003 (lokal) | Konteynerda hammasi `8000` |
| `CRYSTAL_LOG_LEVEL` | `INFO` | |
| `CRYSTAL_HTTP_TIMEOUT_MS` | `3000` | Servislararo so‘rov timeout’i |
| `CRYSTAL_OUTBOX_INTERVAL_MS` | `500` | Outbox tekshirish oralig‘i |
| `CRYSTAL_STARTUP_TIMEOUT_S` | `60` | Bazani kutish |

auth-service:

| O‘zgaruvchi | Standart | Izoh |
| --- | --- | --- |
| `CRYSTAL_JWT_SECRET` | (compose’da dev qiymat) | Imzo kaliti, ≥ 32 belgi. Faqat auth-service oladi. `openssl rand -base64 48` |
| `CRYSTAL_ADMIN_USERNAME` / `CRYSTAL_ADMIN_PASSWORD` | `admin` / `admin_dev_password` | Birinchi ishga tushishda yaratiladi; keyin o‘zgartirilmaydi |
| `CRYSTAL_ACCESS_TOKEN_TTL_S` | `900` | Access token muddati |
| `CRYSTAL_REFRESH_TOKEN_TTL_S` | `604800` | Refresh token muddati (7 kun) |
| `CRYSTAL_AUTH_SERVICE_URL` | `http://localhost:8004` | courier-service uchun (kuryer loginini tekshirish) |

`.env` (faqat compose o‘qiydi, servislarga to‘g‘ridan-to‘g‘ri berilmaydi):
`CRYSTAL_PUBLISH_PORT`, `CRYSTAL_LOG_LEVEL`, `AUTH_DB_PASSWORD`, `ORDER_DB_PASSWORD`,
`COURIER_DB_PASSWORD`, `TRACKING_DB_PASSWORD`, `CRYSTAL_JWT_SECRET`, `CRYSTAL_ADMIN_*`,
`RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_UI_PORT`.
Har bir servis konteyneriga faqat **o‘z bazasining** paroli tushadi.

> `.env.example`dagi parollar faqat lokal uchun. Serverda hammasini almashtiring.
> Parollarda faqat harf, raqam va `_` ishlating — ular URL ichiga qo‘yiladi.

## GitHub Codespaces (Docker o‘rnatmasdan)

`.devcontainer/` brauzerdagi to‘liq Docker muhitini sozlaydi: Codespace ochilganda
`.devcontainer/start.sh` `.env`ni yaratadi, stack’ni ko‘taradi, 8000 portni ommaviy qilishga
urinadi va havolani chiqaradi. CI’ning `codespace` job’i aynan shu devcontainer’ni yig‘ib, ichida
smoke testni ishlatadi. Namoyish qadamlari: [demo.md](demo.md).

## Docker’siz (lokal ishlab chiqish)

```sh
make test                 # 39 ta test: SQLite + xotiradagi shina, tashqi kutubxonasiz
make run-auth             # :8004
make run-order            # :8001
make run-courier          # :8002
make run-tracking         # :8003
```

Diqqat: Docker’siz har bir servis o‘z jarayonida xotiradagi shinadan foydalanadi, shuning uchun
hodisalar boshqa servisga **yetib bormaydi**. To‘liq ssenariy uchun `docker compose` ishlating.

## Loglar

```sh
docker compose logs -f order-service courier-service tracking-service gateway
docker compose logs --no-log-prefix | grep <X-Request-ID>   # bitta so‘rov izi
```

```json
{"ts": "2026-11-22T11:50:21+0000", "level": "INFO", "service": "order-service", "logger": "crystal.http", "msg": "POST /api/v1/orders 201 8.0ms", "request_id": "00b85a43…"}
```

## RabbitMQ panel

`http://localhost:15672` (login/parol `.env`dan). Ko‘rish mumkin: `crystal.events` exchange,
`courier-service.events`, `tracking-service.events` navbatlari va ularning `*.dlq` navbatlari.
DLQ’da xabar paydo bo‘lsa — servis logida shu hodisa bo‘yicha `exc` maydonini qidiring.

## Backup va tiklash

Har bir baza alohida zaxiralanadi:

```sh
for s in auth order courier tracking; do
  docker compose exec -T "$s-db" pg_dump -U "$s" -d "$s" --format=custom > "backup-$s-$(date +%F).dump"
done

# Tiklash (masalan, order)
docker compose stop order-service
docker compose exec -T order-db pg_restore -U order -d order --clean --if-exists < backup-order-2026-11-22.dump
docker compose start order-service
```

tracking-db read model: uni yo‘qotish xavfli emas, lekin hozircha hodisalarni qayta o‘ynatish
(replay) vositasi yo‘q — shuning uchun uni ham zaxiralang.

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` har bir `main` PR va push’da:

1. **test** — testlar Python 3.9 va 3.13 da (tashqi kutubxonasiz).
2. **codespace** — `.devcontainer` yig‘iladi, ichida stack ko‘tariladi va smoke test ishlaydi.
3. **stack** —
   `docker compose config`, obraz ichida testlar, butun stack `up --wait`,
   `smoke_test.sh` (gateway orqali to‘liq hayot sikli, 409/404, `/internal` yopiqligi, tracking
   hodisalar orqali yangilanishi) va `resilience_test.sh`:
   - har bir servis boshqa servis bazasini tarmoqda ko‘rmasligi (6 juftlik);
   - RabbitMQ to‘xtatilganda buyurtma yaratilishi, `degraded` holat va broker qaytgach hodisa yetib borishi;
   - servislar va bazalar qayta ishga tushirilgandan keyin ma’lumot saqlanishi.
4. Har doim loglar chiqariladi va `down --volumes` bilan tozalanadi.

## Nosozliklarni bartaraf etish

| Belgisi | Sabab | Yechim |
| --- | --- | --- |
| `bind: address already in use` | 8000 yoki 15672 band | `.env`da `CRYSTAL_PUBLISH_PORT` / `RABBITMQ_UI_PORT` |
| Servis `unhealthy`, logda `Baza … tayyor bo‘lmadi` | Baza ko‘tarilmagan yoki parol noto‘g‘ri | `docker compose logs order-db`; parolni o‘zgartirgan bo‘lsangiz volume eski parolni saqlaydi → `down --volumes` |
| `/health/<servis>` → `degraded`, `broker: fail` | RabbitMQ ishlamayapti | `docker compose ps rabbitmq`; hodisalar outbox’da kutadi, broker qaytgach yuboriladi |
| `/api/v1/tracking/{code}` → `404`, lekin buyurtma bor | Hodisa hali yetib kelmagan | 1–2 s kuting; uzoq davom etsa broker va tracking-service loglarini tekshiring |
| `dispatch` → `503` | courier-service ishlamayapti | `docker compose logs courier-service` |
| Har qanday so‘rov → `401` | Token yo‘q yoki muddati o‘tgan (15 daqiqa) | Qayta login yoki `POST /api/v1/auth/refresh` |
| `403 Bu amal uchun ruxsat yo‘q` | Rol mos emas | Rollar jadvali: [api.md](api.md) |
| Admin paroli ishlamaydi | `CRYSTAL_ADMIN_PASSWORD` birinchi ishga tushishdan keyin o‘zgartirilgan | Admin faqat bir marta yaratiladi; `down --volumes` yoki admin orqali yangi foydalanuvchi |
| Codespaces havolasi `404`/login so‘raydi | 8000 port `Private` | PORTS → 8000 → Port Visibility → Public |
| Gateway `503 Servis vaqtincha mavjud emas` | Upstream konteyner o‘chgan | `docker compose ps`, `docker compose up -d --wait` |
| `429` | Rate limit (50 r/s) | Yuklama testlari uchun `gateway/nginx.conf`da `rate`ni oshiring |
