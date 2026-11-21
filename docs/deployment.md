# Docker va deploy

## Talablar

| Vosita | Versiya |
| --- | --- |
| Docker Engine | 24+ |
| Docker Compose | v2.24+ (`env_file.required` uchun) |
| Python (Docker’siz ishlatish) | 3.9+ |

## Dockerfile

Obraz ikki bosqichdan iborat:

| Bosqich | Vazifa |
| --- | --- |
| `test` | Kod va testlarni nusxalaydi, `unittest`ni ishlatadi. Test yiqilsa build to‘xtaydi. |
| `runtime` | Faqat `crystal/` va `app.py`. Testlar ishchi obrazga kirmaydi. |

```sh
docker build --target test -t crystal-logistics:test .   # testlar
docker build --target runtime -t crystal-logistics .     # ishchi obraz
docker run --rm crystal-logistics demo                    # demo
docker run --rm -p 8000:8000 -v crystal-data:/data crystal-logistics   # API
```

Ishchi obraz xususiyatlari:

- **Root emas:** `crystal` foydalanuvchisi (uid/gid 10001). Kod `root`ga tegishli — jarayon o‘z kodini o‘zgartira olmaydi.
- **Ma’lumot faqat `/data`da** (`VOLUME`). Konteyner o‘chirilsa ham baza volume’da qoladi.
- **`HEALTHCHECK`** har 15 s `GET /health`ni tekshiradi; 3 marta ketma-ket xato bo‘lsa konteyner `unhealthy`.
- **`ENTRYPOINT ["python", "-m", "crystal"]`**, `CMD ["serve"]` — istalgan CLI buyrug‘ini argument sifatida berish mumkin (`docker run … crystal-logistics demo`).
- **To‘g‘ri to‘xtash:** server `SIGTERM`ni ushlaydi, joriy so‘rovlarni tugatib chiqadi (`docker stop` 10 s kutmaydi).
- **Kichik kontekst:** `.dockerignore` allowlist — faqat `crystal/`, `tests/`, `app.py` yuboriladi; `.env`, `.git`, lokal baza obrazga tushmaydi.
- **Tashqi bog‘liqlik yo‘q** — `pip install` bosqichi yo‘q, ta’minot zanjiri xavfi minimal.

## compose.yaml

```sh
docker compose up --build --detach --wait   # healthy bo‘lguncha kutadi
docker compose ps
docker compose logs -f api
docker compose down                         # ma’lumot saqlanadi
docker compose down --volumes               # ma’lumot ham o‘chadi
```

| Sozlama | Qiymat | Nega |
| --- | --- | --- |
| `ports` | `${CRYSTAL_PUBLISH_PORT:-8000}:8000` | Host porti `.env`dan o‘zgaradi |
| `volumes` | `crystal-data:/data` | SQLite bazasi restart/qayta yaratishdan keyin saqlanadi |
| `restart` | `unless-stopped` | Xatoda yoki host qayta yuklanganda avtomatik ko‘tariladi |
| `read_only: true` + `tmpfs: /tmp` | | Konteyner fayl tizimiga yozib bo‘lmaydi (faqat `/data` va `/tmp`) |
| `cap_drop: [ALL]`, `no-new-privileges` | | Linux imtiyozlari minimal |
| `healthcheck` | `/health` | `--wait` va `depends_on: condition: service_healthy` uchun |
| `logging` | json-file, 10 MB × 3 | Loglar diskni to‘ldirmaydi |

## Muhit o‘zgaruvchilari

| O‘zgaruvchi | Standart (lokal) | Konteynerda | Izoh |
| --- | --- | --- | --- |
| `CRYSTAL_HOST` | `127.0.0.1` | `0.0.0.0` | Tinglash manzili |
| `CRYSTAL_PORT` | `8000` | `8000` | Konteyner ichidagi port |
| `CRYSTAL_DB_PATH` | `crystal.sqlite3` | `/data/crystal.sqlite3` | SQLite fayli; papka avtomatik yaratiladi |
| `CRYSTAL_LOG_LEVEL` | `INFO` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |
| `CRYSTAL_PUBLISH_PORT` | — | `8000` | Faqat compose: hostdagi port |

`.env.example`ni `.env`ga nusxalang. `.env` git’ga kiritilmaydi (`.gitignore`). Hozircha sir (parol, token) yo‘q; kelajakda ular ham faqat `.env` yoki CI secrets orqali beriladi.

## Loglar

Har bir so‘rov bitta qatorda: metod, yo‘l, status, davomiylik.

```
2026-11-21 12:27:18,144 INFO crystal.api GET /health 200 0.9ms
2026-11-21 12:27:18,223 INFO crystal.api POST /api/v1/orders 201 3.1ms
```

Loglar stdout/stderr’ga yoziladi — `docker compose logs` bilan o‘qiladi.

## Backup va tiklash

```sh
# Backup (konteyner ishlayotgan paytda ham xavfsiz — SQLite backup API)
docker compose exec api python -c "import sqlite3; s=sqlite3.connect('/data/crystal.sqlite3'); d=sqlite3.connect('/data/backup.sqlite3'); s.backup(d); d.close()"
docker compose cp api:/data/backup.sqlite3 ./backup-$(date +%F).sqlite3

# Tiklash
docker compose stop api
docker compose cp ./backup-2026-11-21.sqlite3 api:/data/crystal.sqlite3
docker compose start api
```

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` har bir `main` PR va push’da:

1. Testlar Python 3.9 va 3.13 matritsasida.
2. `docker build --target test` — testlar obraz ichida.
3. Ishchi obraz yig‘iladi, `demo` konteynerda ishlaydi.
4. `docker compose up --wait` — konteyner `healthy` bo‘lishi kutiladi.
5. `scripts/smoke_test.sh` — HTTP orqali to‘liq hayot sikli, `409` va `404` holatlari.
6. Buyurtma yaratiladi, konteyner qayta ishga tushiriladi, buyurtma hali ham borligi tekshiriladi.
7. Har doim loglar chiqariladi va `down --volumes` bilan tozalanadi.

## Nosozliklarni bartaraf etish

| Belgisi | Sabab | Yechim |
| --- | --- | --- |
| `bind: address already in use` | 8000 port band | `.env`da `CRYSTAL_PUBLISH_PORT=8080` |
| Konteyner `unhealthy` | Server ishga tushmadi | `docker compose logs api` |
| `unable to open database file` | `/data` yozib bo‘lmaydi (bind mount egasi boshqa) | Named volume ishlating yoki host papkasini `chown 10001:10001` |
| `database is locked` | Juda ko‘p parallel yozish | Bitta replika ishlating; ko‘p replika uchun PostgreSQL (architecture.md) |
| `env_file … required` xatosi | Eski Compose | Compose v2.24+ ga yangilang |
| `curl: Connection refused` | Konteyner hali ko‘tarilmagan | `docker compose up --wait` ishlating |
