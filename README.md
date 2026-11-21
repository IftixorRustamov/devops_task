# Crystal Logistics

PDP University Unit 4 DevOps. Crystal jamoasi, 2-variant. Logistika va kuryer xizmati.

Buyurtmani yaratish, omborga qabul qilish, kuryerga biriktirish, yo‘lga chiqarish va topshirishni kuzatadigan REST API. Docker konteynerda ishlaydi, ma’lumotlar Docker volume’dagi SQLite bazasida saqlanadi. Tashqi kutubxona yo‘q — faqat Python standart kutubxonasi.

## Tez ishga tushirish (Docker)

Talab: Docker 24+ va Docker Compose v2.24+.

```sh
cp .env.example .env            # ixtiyoriy
docker compose up --build --detach --wait
curl http://localhost:8000/health
./scripts/smoke_test.sh         # to‘liq hayot siklini tekshiradi
```

To‘xtatish: `docker compose down` (ma’lumotlar saqlanadi). Hammasini o‘chirish: `docker compose down --volumes`.

`make help` barcha qisqa buyruqlarni ko‘rsatadi (`make up`, `make smoke`, `make logs`, `make docker-test`…).

## API qisqacha

| Metod | Yo‘l | Vazifa |
| --- | --- | --- |
| `GET` | `/health` | Servis va baza holati |
| `GET` | `/api/v1/warehouses` | Omborlar ro‘yxati |
| `POST` | `/api/v1/orders` | Buyurtma yaratish `{"address": "...", "warehouse_id": 1}` |
| `GET` | `/api/v1/orders/{code}` | Holat va tarix |
| `POST` | `/api/v1/orders/{code}/receive` | Omborga qabul qilish |
| `POST` | `/api/v1/orders/{code}/assign` | Kuryer biriktirish `{"courier": "..."}` |
| `POST` | `/api/v1/orders/{code}/dispatch` | Yo‘lga chiqarish |
| `POST` | `/api/v1/orders/{code}/deliver` | Topshirish |

```sh
curl -X POST localhost:8000/api/v1/orders -H 'Content-Type: application/json' \
     -d '{"address": "Demo manzil"}'
```

To‘liq tavsif, misollar va xato kodlari: [docs/api.md](docs/api.md).

Holatlar: `Yangi → Omborda → Yo‘lda → Yetkazildi`. Bosqichni o‘tkazib yuborish yoki ortga qaytish mumkin emas (`409 Conflict`).

## Docker’siz ishlatish

Python 3.9 yoki yangiroq versiya kerak.

```sh
python3 -m crystal serve --port 8000      # API
python3 -m crystal demo                    # xotiradagi bazada to‘liq demo
python3 app.py create "Demo manzil"        # CLI (eski buyruqlar ham ishlaydi)
python3 app.py receive KOD
python3 app.py assign KOD "Demo kuryer"
python3 app.py dispatch KOD
python3 app.py deliver KOD
python3 app.py track KOD
```

CLI ma’lumotni lokal `crystal.sqlite3` faylida saqlaydi (`--db` yoki `CRYSTAL_DB_PATH` bilan o‘zgartiriladi).

## Loyiha tuzilmasi

```
crystal/
  config.py       muhit o‘zgaruvchilari (CRYSTAL_*)
  domain.py       holatlar, o‘tishlar, xato turlari
  db.py           SQLite ulanishi, sxema, tranzaksiya
  repository.py   SQL so‘rovlar
  service.py      biznes mantiq (OrderService)
  api/server.py   HTTP REST API
  cli.py          buyruqlar qatori
tests/            unit, API va CLI testlari
scripts/          smoke test
Dockerfile        test + runtime bosqichli obraz
compose.yaml      servis, volume, healthcheck
```

Qatlamlar va qarorlar: [docs/architecture.md](docs/architecture.md).

## Testlar

```sh
python3 -m unittest discover -s tests -v       # lokal
docker build --target test .                   # Docker ichida
```

GitHub Actions har bir `main` PR’ida testlarni Python 3.9 va 3.13 da ishlatadi, Docker obrazini yig‘adi, compose bilan ko‘taradi, smoke test va restartdan keyin ma’lumot saqlanishini tekshiradi.

## Hujjatlar

- [Arxitektura](docs/architecture.md) — qatlamlar, ma’lumotlar modeli, holat mashinasi
- [API](docs/api.md) — endpointlar, misollar, xatolar
- [Docker va deploy](docs/deployment.md) — obraz, compose, sozlamalar, backup, nosozliklar
- [Qarorlar](docs/decisions.md) · [Jamoa kelishuvi](docs/team-charter.md) · [Kirish huquqlari](docs/access.md) · [Stand-up](docs/meetings.md)
