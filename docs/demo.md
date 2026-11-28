# O‘qituvchiga namoyish (GitHub Codespaces)

Kompyuteringizda Docker shart emas — hammasi GitHub serverida, brauzerda ishlaydi.

## 1. Codespace ochish (bir marta, ~5 daqiqa)

1. GitHub’da repozitoriyni oching → yashil **Code** tugmasi → **Codespaces** → **Create codespace on main**.
2. Brauzerda VS Code ochiladi. Pastdagi terminalda avtomatik ishga tushadi:
   `Crystal Logistics ishga tushirilmoqda…` — birinchi marta 3–5 daqiqa (obrazlar yig‘iladi).
3. Oxirida chiqadi: `Tayyor! Namoyish sahifasi: https://<nom>-8000.app.github.dev`

Havola o‘qituvchida ochilmasa: pastdagi **PORTS** oynasi → `8000` qatori → o‘ng tugma →
**Port Visibility → Public**.

> Codespace 30 daqiqa harakatsiz tursa to‘xtaydi (GitHub tekin limitini tejaydi). Namoyishdan oldin
> github.com/codespaces sahifasidan uni qayta **Open** qiling — stack o‘zi qayta ko‘tariladi
> (ma’lumotlar saqlanadi). Ishlatib bo‘lgach **Stop codespace** qiling.

Terminalda tekshirish: `./scripts/smoke_test.sh` — 50 dan ortiq tekshiruv, oxirida
`Smoke test muvaffaqiyatli`.

## 2. Namoyish ssenariysi (5–7 daqiqa)

Havolani oching — **Crystal Logistics** boshqaruv paneli. O‘ngdagi **So‘rovlar jurnali** har bir
so‘rovning status kodini ko‘rsatadi (tafsilot uchun qatorni oching). Dizayn sabablari: [design.md](design.md).

| # | Qadam | Nimani ko‘rsatadi |
| --- | --- | --- |
| 1 | Noto‘g‘ri parol bilan kirishga urinib ko‘ring | `401`, «Login yoki parol noto‘g‘ri» |
| 2 | `admin` / `admin_dev_password` bilan kiring → **Namoyish foydalanuvchilarini yaratish** | auth-service JWT beradi; `op1`, `ali`, `vali` yaratiladi (parol `demo-parol-1`) |
| 3 | **Chiqish** → kirish sahifasida **op1 · operator** → **Kirish** → manzil kiriting → **Buyurtma yaratish** | order-service, `201`; marshrut va sariq kod yorlig‘i paydo bo‘ladi |
| 4 | **Omborga qabul qilish** → **Yo‘lga chiqarish** | `409` — «Avval buyurtmaga kuryer biriktiring» (biznes qoidasi) |
| 5 | Kuryer logini `ali` → **Kuryer biriktirish** → **Yo‘lga chiqarish** | courier-service order-service’dan holatni, auth-service’dan kuryerni so‘raydi |
| 6 | **Chiqish** → **vali · kuryer** | «Sizga hali buyurtma biriktirilmagan» — boshqa kuryerning buyurtmasi ko‘rinmaydi |
| 7 | **Chiqish** → **ali · kuryer** → **Topshirildi deb belgilash** | Kuryer faqat O‘Z buyurtmasini topshiradi, `200` |
| 8 | O‘ngda **Buyurtmani kuzatish** (kod avtomatik qo‘yilgan) → **Kuzatish** | tracking-service, tokensiz; hodisalardan qurilgan, manzil va kuryer nomi yo‘q |

Terminalda qo‘shimcha ko‘rsatish mumkin:

```sh
docker compose ps                                   # 10 ta konteyner, hammasi healthy
docker compose logs --no-log-prefix order-service | tail -5   # JSON loglar, request_id
curl -s localhost:8000/api/v1/orders -X POST -d '{}' # 401 — token yo‘q
./scripts/resilience_test.sh                        # bazalar izolyatsiyasi, broker o‘chishi, restart
```

RabbitMQ paneli: PORTS → `15672` → globus belgisi (login `crystal` / `crystal_dev_password`) —
`crystal.events` exchange va servis navbatlari.

## 3. Savol bo‘lsa — qisqa javoblar

- **Nega 4 ta baza?** Database-per-service: har bir servis o‘z ma’lumotining egasi, boshqa servis
  unga tarmoqda ham ulana olmaydi (`resilience_test.sh` 12 juftlikni tekshiradi).
- **Token qayerda tekshiriladi?** Gateway (nginx `auth_request`) har so‘rovni auth-service’da
  tekshiradi; servislar faqat rolni ko‘radi. Imzo kaliti faqat auth-service’da.
- **Broker o‘chsa?** Buyurtmalar yaratilaveradi (outbox), hodisalar broker qaytganda yetib boradi.
- **Token o‘g‘irlansa?** Access token 15 daqiqa yashaydi; refresh token bir martalik — qayta
  ishlatilsa foydalanuvchining barcha sessiyalari bekor qilinadi.
