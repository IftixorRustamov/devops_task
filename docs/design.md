# Interfeys dizayni: nima qilindi va nega

Fayl: `gateway/demo/index.html` — gateway `/` manzilida beradigan boshqaruv paneli.
Bitta HTML fayl, tashqi kutubxona, shrift yoki rasm yo‘q.

## 1. Kim uchun va nima uchun

| | |
| --- | --- |
| **Foydalanuvchilar** | Operator (buyurtmalarni boshqaradi), kuryer (yetkazadi), admin (xodimlarni yaratadi), mijoz (kodi bilan kuzatadi) va namoyishni ko‘rayotgan o‘qituvchi |
| **Asosiy vazifa** | Buyurtmani marshrut bo‘ylab olib borish va har qadamda tizim nima qilganini ko‘rsatish |
| **Muhit** | Codespaces ommaviy havolasi, noutbuk yoki telefon, internet sekin bo‘lishi mumkin |

Shu uchun dizayn ikki narsaga qurilgan: **buyurtma qayerda** (marshrut) va **tizim nima javob berdi**
(so‘rovlar jurnali). Qolgan hamma narsa sokin turadi.

## 2. Asosiy element: marshrut

```
  ●━━━━━━━━━━━●━━━━━━━━━━━◉───────────○
Yangi      Omborda      Yo‘lda      Yetkazildi
14:02       14:05        14:09
                          ┌──────────────────────────────┐
                          │ Keyingi qadam                │
                          │ [Topshirildi deb belgilash]  │
                          └──────────────────────────────┘
```

- Buyurtmaning to‘rt holati — backend’dagi holat mashinasining o‘zi (`order-service/domain.py`).
  Interfeys tizim qoidasini **ko‘rinadigan qiladi**: bosqichni o‘tkazib bo‘lmaydi, ortga qaytib bo‘lmaydi.
- **Faqat keyingi qadam tugmasi** ko‘rsatiladi. Eski variantda 5 ta tugma bir qatorda turardi va
  foydalanuvchi qaysi biri hozir mumkinligini taxmin qilardi. Endi xato qilish imkoniyati kamroq.
- O‘tgan bekatlar ✓ va vaqt bilan, joriysi rang halqasi bilan, kelajakdagilari kulrang.
- Telefonda (600 px dan tor) marshrut vertikal ro‘yxatga aylanadi — gorizontal chiziq sig‘maydi.
- Yagona animatsiya — chiziqning to‘lishi (0,45 s). U foydalanuvchi harakatiga javob: «holat
  o‘zgardi». Boshqa bezak animatsiyalari yo‘q; `prefers-reduced-motion` yoqilsa u ham o‘chadi.

## 3. Ranglar

| Token | Qiymat | Qayerda | Nega |
| --- | --- | --- | --- |
| `--concrete` | `#E9EDF1` | Sahifa foni | Ombor betoni kabi sovuq kulrang. Oq ish maydoni undan ajralib turadi |
| `--surface` | `#FFFFFF` | Ish maydoni | Ma’lumot o‘qiladigan joy — eng yuqori kontrast |
| `--ink` | `#1B2430` | Matn, yuqori panel, asosiy tugma | Qora emas, to‘q ko‘k-kulrang: yumshoqroq, lekin oq bilan 15,6:1 |
| `--ink-2` | `#4A5565` | Izohlar, sarlavha ostidagi matn | Ikkinchi daraja, lekin baribir AA (7,6:1) |
| `--line` | `#D3DAE2` | Chegaralar | Soya o‘rniga — tekis, tez chiziladi |
| `--label` | `#FFC933` | Faqat buyurtma kodi «yorlig‘i» va logotip | Yuk yorliqlari va ogohlantirish lentasi rangi. **Faqat** kod uchun — shuning uchun ko‘z darhol kodni topadi |

### Holat ranglari — logistikaning o‘z tili

| Holat | Matn / fon | Ma’nosi |
| --- | --- | --- |
| Yangi | `#5B6676` / `#EEF1F4` | Neytral: hali hech narsa bo‘lmagan |
| Omborda | `#9A6300` / `#FFF3D6` | Sariq-jigarrang: karton, tokcha, «kutmoqda» |
| Yo‘lda | `#1F55C7` / `#E5EDFF` | Ko‘k: harakat, yo‘l |
| Yetkazildi | `#137344` / `#DDF5E8` | Yashil: yakunlandi |

Bir holat **hamma joyda bir xil rangda**: belgi (chip), marshrut bekati, keyingi qadam tugmasi,
kuryer jadvali va ommaviy kuzatuv. Masalan, «Omborga qabul qilish» tugmasi amber — bosilsa buyurtma
amber holatga o‘tadi. Rang faqat yagona belgi emas: har doim holat nomi matn bilan yoziladi
(rang ajratolmaydiganlar uchun).

### Kontrast (WCAG 2.1, hisoblab tekshirilgan)

| Juftlik | Nisbat | Talab (AA) |
| --- | --- | --- |
| Asosiy matn / oq | 15,65 | 4,5 |
| Ikkinchi darajali matn / oq | 7,56 | 4,5 |
| Oq / amber tugma | 5,05 | 4,5 |
| Oq / ko‘k tugma | 6,60 | 4,5 |
| Oq / yashil tugma | 5,89 | 4,5 |
| Omborda belgisi (eng past) | 4,58 | 4,5 |
| Matn / sariq yorliq | 10,18 | 4,5 |
| Xato matni / xato foni | 9,26 | 4,5 |

## 4. Tugmalar

| Tur | Ko‘rinishi | Qachon |
| --- | --- | --- |
| **Asosiy** | To‘q (`--ink`) fon, oq matn | Ekrandagi bitta asosiy harakat: «Kirish», «Buyurtma yaratish», «Foydalanuvchi yaratish» |
| **Qadam** | Holat rangida | Marshrutdagi keyingi qadam — rangi qaysi holatga o‘tishini bildiradi |
| **Ikkinchi darajali** | Oq fon, chegara | Yordamchi amallar: «Kuryer biriktirish», «Ochish», «Kuzatish», «Ro‘yxatni yangilash» |
| **Havola-tugma** | Tagiga chizilgan ko‘k matn | Kichik amallar jadval ichida: «Ochish», «Yangilash» |
| **Sokin** | Shaffof, oq chegara | To‘q yuqori panelda: «Chiqish» |

Umumiy qoidalar:

- **Balandlik 42 px** (kichik variant 34 px) — barmoq bilan bosishga yetarli, maydonlar bilan bir xil
  balandlikda, shuning uchun forma qatorida tekis turadi.
- **Matn — fe’l, natijani aytadi:** «Buyurtma yaratish», «Omborga qabul qilish», «Topshirildi deb
  belgilash». «OK», «Yuborish» kabi umumiy so‘zlar yo‘q. Tugma nomi va natija xabari bir xil so‘z
  bilan: «Kuryer biriktirish» → «ali biriktirildi».
- **Yuklanish holati:** bosilgach tugma o‘chadi va aylanuvchi belgi chiqadi (`aria-busy`) — sekin
  tarmoqda ikki marta bosib, ikki buyurtma yaratib yuborishning oldi olinadi.
- **Klaviatura:** har bir tugma va maydonda aniq ko‘k fokus halqasi (`:focus-visible`), Tab bilan
  butun panelni boshqarish mumkin.
- O‘chirilgan tugma 45 % shaffof va `not-allowed` kursor bilan — masalan, kuryer biriktirilgandan keyin
  «Kuryer biriktirilgan».

## 5. Shrift

- **Tizim shrifti** (`system-ui`, Segoe UI, Roboto…). Sabab: gateway’ning Content-Security-Policy
  qoidasi tashqi manbalarni bloklaydi (`default-src 'self'`), namoyish internetsiz ham ishlashi kerak
  va shrift yuklanmagani uchun sahifa darhol ochiladi. Shaxsiyat shriftdan emas, marshrut va yorliqdan keladi.
- **Monospace faqat kodlar uchun** — `CRY-…` va API yo‘llari. Bu identifikatorlar: ularni nusxalash,
  solishtirish va o‘qib berish kerak, belgilar adashmasligi muhim (`0`/`O`, `1`/`l`).
- O‘lcham shkalasi: 24 (ekran sarlavhasi) → 17 (blok) → 15 (asosiy matn) → 13 (izoh, yorliq).
  Vaqtlar `tabular-nums` bilan — jurnal ustunida raqamlar sakramaydi.
- Matn qatori 62 belgigacha cheklangan (`max-width: 62ch`) — uzun qatorlarni o‘qish qiyin.

## 6. Maket

```
┌──────────────────────── yuqori panel: logotip · foydalanuvchi · rol · Chiqish ────────┐
├───────────────────────────────────────────────┬──────────────────────────────────────┤
│ Ish maydoni (oq) — rolga qarab o‘zgaradi       │ Yon panel (fon ustida, kartasiz)     │
│  • kirish                                      │  • ommaviy kuzatuv                   │
│  • operator/admin: yangi buyurtma, marshrut    │  • so‘rovlar jurnali                 │
│  • kuryer: mening yetkazmalarim                │                                      │
│  • admin: foydalanuvchilar                     │                                      │
└───────────────────────────────────────────────┴──────────────────────────────────────┘
```

- **Rolga qarab ekran.** Avvalgi sahifada barcha bo‘limlar bir xil kartalarda turardi. Endi har bir
  rol faqat o‘z ishini ko‘radi — bu backend’dagi ruxsatlar bilan bir xil (`require_role`).
  Tugmani yashirish xavfsizlik emas: ruxsatni server tekshiradi, interfeys faqat chalkashlikni kamaytiradi.
- **Bir xil kartalar ishlatilmadi.** Asosiy ish bitta oq maydonda, ichidagi bo‘limlar ingichka chiziq
  bilan ajratilgan. Yon panel kartasiz — u ikkinchi darajali ekani shundan ham ko‘rinadi.
- **Chapga tekislangan** matn va formalar — ko‘z bir chiziq bo‘ylab yuradi.
- 960 px dan tor ekranda yon panel ish maydoni ostiga tushadi; 480 px dan torda foydalanuvchi nomi
  yashiriladi (rol qoladi) — yuqori panel bir qatorda qoladi.

## 7. Matnlar va xatolar

- O‘zbek tilida, oddiy so‘zlar bilan: «webhook», «endpoint» emas — «buyurtma», «kuryer», «topshirish».
- **Bo‘sh holat — keyingi qadam:** «Hali buyurtma yo‘q. Yuqorida manzil kiriting va «Buyurtma
  yaratish»ni bosing.»
- **Xato nima bo‘lganini va nima qilish kerakligini aytadi:** «Avval buyurtmaga kuryer biriktiring.»
  Server xabari to‘g‘ridan-to‘g‘ri ko‘rsatiladi — u allaqachon o‘zbekcha va aniq.
- Login xatosida qaysi maydon noto‘g‘riligi aytilmaydi («Login yoki parol noto‘g‘ri») — backend kabi,
  login borligini oshkor qilmaslik uchun. 429 uchun alohida: «Bir daqiqadan so‘ng qayta urinib ko‘ring.»
- Xabarlar `role="alert"` / `role="status"` bilan — ekran o‘qish dasturi ularni ovoz chiqarib o‘qiydi.

## 8. So‘rovlar jurnali — namoyish uchun

Har bir so‘rov: status kodi (yashil 2xx, qizil 4xx/5xx), odam tilidagi tavsif («Kuryer ali
biriktirildi»), vaqt. Texnik tafsilot (`POST /api/v1/...` va JSON javob) yopiq `<details>` ichida —
o‘qituvchi xohlasa ochadi, aks holda ekranni to‘ldirmaydi. Tokenlar jurnalda qisqartirib ko‘rsatiladi.

Izohda aytilganidek: 401, 403, 409 — bu xato emas, tizim qoidalari ishlayotganining isboti.
Shuning uchun ular yashirilmaydi.

## 9. Xavfsizlik va texnik tanlovlar

- **Token faqat sahifa xotirasida** (JavaScript o‘zgaruvchisi), `localStorage`da emas — sahifa
  yopilsa yo‘qoladi, boshqa skript o‘qiy olmaydi. Access token tugasa (15 daqiqa), sahifa refresh
  token bilan **jimgina yangilaydi** va so‘rovni qaytaradi — namoyish o‘rtasida chiqib ketmaydi.
- Barcha server ma’lumotlari HTML’ga qo‘yishdan oldin `esc()` bilan tozalanadi (XSS’dan himoya,
  masalan manzil maydoniga `<script>` yozilsa).
- Gateway sahifaga qat’iy CSP sarlavhasi qo‘yadi: faqat o‘z manbalari, iframe ichiga joylab bo‘lmaydi.
- «Namoyish foydalanuvchilarini yaratish» tugmasi (faqat admin) `op1`, `ali`, `vali` hisoblarini bir
  bosishda yaratadi; allaqachon bo‘lsa (`409`) — xato hisoblanmaydi. Bu faqat namoyish qulayligi:
  oddiy `POST /api/v1/auth/users` endpointini chaqiradi, yangi backend imkoniyati emas.

## 10. Tekshiruv

- Chrome’da (Playwright) to‘liq ssenariy: noto‘g‘ri login, admin namoyish hisoblari, buyurtma,
  kuryersiz yo‘lga chiqarish (409), biriktirish, boshqa kuryer (bo‘sh ro‘yxat), o‘z kuryeri topshiradi,
  ommaviy kuzatuv, telefon o‘lchami (390 px). JavaScript xatosi yo‘q.
- Kontrast nisbatlari WCAG formulasi bilan hisoblandi (3-bo‘lim).

## Keyingi qadamlar (agar kerak bo‘lsa)

- Qorong‘i rejim: tokenlar allaqachon o‘zgaruvchilarda, faqat ikkinchi palitra kerak.
- Buyurtmalar ro‘yxati serverdan (hozir faqat shu sessiyada yaratilganlar) — backend’ga
  `GET /api/v1/orders` qo‘shishni talab qiladi.
