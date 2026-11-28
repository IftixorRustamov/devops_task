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

## 9. Bo‘limlar (tablar)

Yuqori panel ostida rolga qarab tablar:

| Rol | Tablar |
| --- | --- |
| Tizimga kirmagan | Kirish, Arxitektura |
| Operator | Buyurtmalar, Dashboard, Arxitektura |
| Admin | Buyurtmalar, Dashboard, Foydalanuvchilar, Arxitektura |
| Kuryer | Yetkazmalarim, Arxitektura |

Dashboard va Arxitektura keng ekran talab qiladi — ularda o‘ng panel (kuzatuv, jurnal) yashiriladi
va ish maydoni butun kenglikni oladi. Telefonda tablar gorizontal suriladi, faol tab ko‘rinishga keltiriladi.

## 10. Dashboard

Ma’lumot manbalari: `GET /api/v1/stats` (order-service) va `GET /api/v1/couriers/stats`
(courier-service) — har biri **o‘z bazasidan** hisoblaydi, servislar bir-birining bazasiga
murojaat qilmaydi. Sahifa ochiq turganda 10 soniyada yangilanadi (fon yorlig‘ida — yo‘q).
Avtomatik yangilanish so‘rovlari jurnalga yozilmaydi, aks holda jurnal to‘lib ketadi.

| Element | Shakl | Nega aynan shu |
| --- | --- | --- |
| Jami, yo‘lda, yetkazilgan %, o‘rtacha vaqt | **Raqam plitalari** (grafik emas) | Bitta raqam — bitta javob; grafik chizish ortiqcha |
| Holatlar bo‘yicha | Gorizontal bar | Kategoriyalarni solishtirish; holat nomi chapda matn bilan, rang — holat rangi |
| Oxirgi 24 soat | Ustunli grafik, bitta rang | Vaqt bo‘yicha miqdor; bo‘sh soatlar ham 0 bilan ko‘rsatiladi — oqim uzilishi ko‘rinadi |
| Bosqichlar davomiyligi | Gorizontal bar | Qaysi bosqich sekin — darhol ko‘rinadi; rang — bosqich yakunidagi holat |
| Kuryerlar yuklamasi | Ikki qismli bar + legend | «Topshirilgan» va «qo‘lida» — bitta kuryerning ikki qismi, birgalikda jami |
| Oxirgi buyurtmalar | Jadval | Aniq kodlar va vaqtlar kerak; «Ochish» buyurtmani marshrutda ochadi |

Grafik qoidalari:

- **Tashqi kutubxonasiz SVG** — CSP faqat o‘z manbalariga ruxsat beradi, sahifa internetsiz ishlaydi.
- Barlar ingichka (22 px), uchi 4 px yumaloq, asosi to‘g‘ri; ikki qism orasida 2 px oq tirqish
  (chegara chizig‘i o‘rniga).
- Yorliqlar tanlab: qiymat bar uchida, o‘qda faqat «toza» raqamlar (0, yarmi, maksimum).
- Matn hech qachon ma’lumot rangida emas — har doim matn ranglarida; rang faqat belgi (bar)da.
- **Ikki o‘qli grafik yo‘q** — har bir o‘lchov o‘z grafigida.
- **Har bir grafikda hover/fokus tooltip** (sichqoncha yoki Tab tugmasi bilan) va
  **«Jadval ko‘rinishi»** — rangni ko‘rmaydigan yoki ekran o‘qish dasturi ishlatadiganlar uchun
  xuddi shu raqamlar jadvalda. SVG’da `aria-label` bilan qisqa matnli tavsif ham bor.
- Bo‘sh holat: «Hali buyurtma yo‘q. «Buyurtmalar» bo‘limida birinchisini yarating.»

### Rang palitrasini tekshirish

Holat ranglari grafikda kategoriya ranglari sifatida ishlatiladi, shuning uchun ular rang ko‘rish
nuqsonlari simulyatsiyasi bilan tekshirildi (OKLab ΔE):

| Tekshiruv | Natija |
| --- | --- |
| Yorug‘lik diapazoni | o‘tdi |
| Rang ko‘rish nuqsonida farqlanish (eng yomon qo‘shni juftlik) | o‘tdi, ΔE 13,3 (≥ 8 talab) |
| Oddiy ko‘zda farqlanish | o‘tdi, ΔE 15,1 (≥ 15 talab) |
| Fonga nisbatan kontrast | o‘tdi, hammasi ≥ 3:1 |
| Rang to‘yinganligi | «Yangi» kulrang-ko‘k (`#5B6676`) **ataylab** past |

«Yangi» uchun binafsha va boshqa to‘yingan ranglar sinab ko‘rildi — ular «Yo‘lda» ko‘kidan
ajralmadi (ΔE 2–4). «Yangi» — hali hech narsa bo‘lmagan holat, neytral rang uning ma’nosiga
mos. Bu murosa xavfsiz, chunki holat grafigida **har bir bar holat nomi bilan yozilgan** —
rang yagona belgi emas.

## 11. Arxitektura (jonli diagramma)

Tizim tuzilishi chizma sifatida, har bir tugun jonli holat bilan. Sahifa har 5 soniyada
`/health`, `/health/auth|order|courier|tracking` endpointlarini chaqiradi (ular ommaviy, token
kerak emas — shuning uchun bu tab tizimga kirmasdan ham ochiladi).

- **Tugunlar** — gateway, 4 servis, 4 baza, RabbitMQ. Ramka rangi va burchakdagi belgi:
  ✓ yashil — ishlaydi, ! amber (uzuq ramka) — qisman (masalan broker yo‘q, hodisalar outbox’da
  kutmoqda), ✕ qizil — ishlamaydi. Rang + belgi + ramka shakli — faqat rangga tayanmaydi.
- Baza holati servisning `checks.database` qiymatidan, RabbitMQ holati servislarning
  `checks.broker` qiymatlaridan olinadi — bazalar va broker tashqaridan to‘g‘ridan-to‘g‘ri
  tekshirilmaydi (ular yopiq tarmoqda).
- **Chiziqlar uch xil:** to‘q uzluksiz — sinxron HTTP; amber uzuq — RabbitMQ hodisasi
  (o‘q yo‘nalishi: chiqaradi / oladi); och kulrang — servisning o‘z bazasi. Pastda legend.
- Uzuq ramka bilan «Ichki tarmoq» zonasi — tashqaridan faqat gateway orqali kirish mumkinligini
  ko‘rsatadi.
- Diagramma ostida **jadval**: har bir servisning holati, baza/broker/outbox tekshiruvlari va
  javob vaqti (ms). Undan keyin to‘rtta asosiy arxitektura qarori qisqa matnda.

**Namoyishda:** terminalda `docker compose stop rabbitmq` — 5 soniyada RabbitMQ tuguni qizil,
servislar «qisman» bo‘ladi; buyurtma yaratish baribir ishlaydi. `docker compose start rabbitmq` —
hammasi yana yashil, kutib turgan hodisalar yetib boradi.

## 12. Xavfsizlik va texnik tanlovlar

- **Token faqat sahifa xotirasida** (JavaScript o‘zgaruvchisi), `localStorage`da emas — sahifa
  yopilsa yo‘qoladi, boshqa skript o‘qiy olmaydi. Access token tugasa (15 daqiqa), sahifa refresh
  token bilan **jimgina yangilaydi** va so‘rovni qaytaradi — namoyish o‘rtasida chiqib ketmaydi.
- Barcha server ma’lumotlari HTML’ga qo‘yishdan oldin `esc()` bilan tozalanadi (XSS’dan himoya,
  masalan manzil maydoniga `<script>` yozilsa).
- Gateway sahifaga qat’iy CSP sarlavhasi qo‘yadi: faqat o‘z manbalari, iframe ichiga joylab bo‘lmaydi.
- «Namoyish foydalanuvchilarini yaratish» tugmasi (faqat admin) `op1`, `ali`, `vali` hisoblarini bir
  bosishda yaratadi; allaqachon bo‘lsa (`409`) — xato hisoblanmaydi. Bu faqat namoyish qulayligi:
  oddiy `POST /api/v1/auth/users` endpointini chaqiradi, yangi backend imkoniyati emas.

## 13. Tekshiruv

- Chrome’da (Playwright) to‘liq ssenariy: noto‘g‘ri login, admin namoyish hisoblari, buyurtma,
  kuryersiz yo‘lga chiqarish (409), biriktirish, boshqa kuryer (bo‘sh ro‘yxat), o‘z kuryeri topshiradi,
  ommaviy kuzatuv, telefon o‘lchami (390 px). JavaScript xatosi yo‘q.
- Dashboard (5 ta buyurtma turli holatlarda, ikki kuryer) va Arxitektura tablari Chrome’da
  ochildi; tooltip, jadval ko‘rinishi va telefon maketi tekshirildi.
- Statistika endpointlari uchun unit va integratsion testlar (hisob-kitob, rol cheklovi).
- Kontrast nisbatlari WCAG formulasi bilan hisoblandi (3-bo‘lim).

## Keyingi qadamlar (agar kerak bo‘lsa)

- Dashboard uchun vaqt oralig‘i filtri (bugun / 7 kun / 30 kun).

- Qorong‘i rejim: tokenlar allaqachon o‘zgaruvchilarda, faqat ikkinchi palitra kerak.
- To‘liq buyurtmalar ro‘yxati sahifalash bilan (hozir Dashboard oxirgi 10 tasini ko‘rsatadi).
