# Mahsulot: tahlil va yaxshilanishlar

Senior product manager nigohi bilan: kim foydalanadi, qayerda qiynaladi va nima qilindi.

## Foydalanuvchilar va ularning vazifasi

| Kim | Asosiy vazifa | Muvaffaqiyat belgisi |
| --- | --- | --- |
| **Operator** | Buyurtmani qabul qilish, kuryerga berish, oxirigacha kuzatish | Kerakli buyurtmani soniyalarda topadi, hech biri «yo‘qolmaydi» |
| **Kuryer** | Posilkani to‘g‘ri odamga, to‘g‘ri manzilga yetkazish | Manzil va telefon qo‘lida, bir bosishda «Topshirildi» |
| **Mijoz** | Posilkasi qayerda ekanini bilish | Havolani ochib holatni ko‘radi, hech kimga qo‘ng‘iroq qilmaydi |
| **Admin** | Jamoani boshqarish | Xodim qo‘shish, rollar |

## Topilgan muammolar

| # | Muammo | Kimga ta’sir | Jiddiyligi |
| --- | --- | --- | --- |
| 1 | Kuryer faqat `CRY-…` kodini ko‘radi: **manzil yo‘q, qabul qiluvchi yo‘q, telefon yo‘q** | Kuryer | Bloklovchi: yetkazib bo‘lmaydi |
| 2 | Buyurtmada **qabul qiluvchi va telefon umuman yo‘q** | Kuryer, operator | Bloklovchi |
| 3 | Operator buyurtmani **topa olmaydi**: qidiruv va filtr yo‘q, faqat oxirgi 10 ta | Operator | Yuqori |
| 4 | Buyurtmani **bekor qilib bo‘lmaydi** (sohada ~5–10% buyurtma bekor bo‘ladi) | Operator | Yuqori |
| 5 | Mijozga **kuzatuv havolasi** yo‘q — kodni qo‘lda terish kerak | Mijoz | O‘rta |
| 6 | Har qanday kuryer **istalgan buyurtma holatini** ko‘ra olardi | Xavfsizlik | O‘rta |

## Ustuvorlik (ta’sir / harakat)

| Yechim | Ta’sir | Harakat | Qaror |
| --- | --- | --- | --- |
| Qabul qiluvchi, telefon + kuryerga to‘liq ma’lumot | Juda yuqori | O‘rta | **Qilindi** |
| Qidiruv va holat filtri | Yuqori | Past | **Qilindi** |
| Bekor qilish (sabab bilan) | Yuqori | Past | **Qilindi** |
| Kuzatuv havolasi | O‘rta | Juda past | **Qilindi** |
| Buyurtmani kuryer faqat o‘zi ko‘radi | O‘rta | Juda past | **Qilindi** |
| SMS xabarnoma mijozga | Yuqori | Yuqori (SMS provayder) | Keyingi bosqich |
| Topshirish isboti (rasm / imzo) | O‘rta | Yuqori | Keyingi bosqich |
| Kechikayotgan buyurtmalar (SLA) | O‘rta | O‘rta | Keyingi bosqich |

## Nima qilindi

**Buyurtma yaratish.** Uchta majburiy maydon: qabul qiluvchi, telefon, manzil. Telefon har qanday
yozuvda qabul qilinadi («90 123 45 67», «+998 90 123-45-67») va `+998901234567` ko‘rinishiga
keltiriladi; noto‘g‘ri bo‘lsa — aniq xato. Forma «Yangi buyurtma» tugmasi bilan ochiladi va
ro‘yxatni to‘sib turmaydi.

**Buyurtmalar ro‘yxati.** Qidiruv (kod, ism, telefon, manzil) va holat filtrlari, har birida son:
«Yangi 2», «Yo‘lda 1». Sahifalab yuklash («Yana ko‘rsatish»).

**Buyurtma kartasi.** Qabul qiluvchi, bosiladigan telefon, manzil, kuryer, marshrut va bitta keyingi
qadam. «Bekor qilish» — faqat «Yangi» va «Omborda» holatida (yo‘lga chiqqan posilka kuryerda),
sabab so‘raladi va tasdiqlanadi. Havola tugmasi mijoz uchun kuzatuv havolasini nusxalaydi.

**Kuryer ekrani.** Har bir faol yetkazma — karta: qabul qiluvchi, katta harf bilan manzil,
«Qo‘ng‘iroq» va «Topshirildi». Yakunlanganlari pastda yig‘ilgan. Kuryer **faqat o‘ziga biriktirilgan**
buyurtma tafsilotlarini ko‘radi (manzil va telefon — shaxsiy ma’lumot).

**Mijoz havolasi.** `/?track=CRY-…` — sahifa kuzatuv bo‘limida darhol ochiladi. Ommaviy javobda
manzil, telefon va kuryer ismi yo‘q.

**Texnik asos.** order-service’ga versiyalangan migratsiyalar qo‘shildi (`schema_migrations`):
mavjud bazalar (masalan, Codespaces’dagi) ma’lumot yo‘qotmasdan yangi ustunlarni oladi.
Yangi endpointlar: `GET /api/v1/orders?q=&status=&limit=&offset=`, `POST /api/v1/orders/{code}/cancel`.

## Muvaffaqiyatni qanday o‘lchaymiz

| Ko‘rsatkich | Qayerdan | Maqsad |
| --- | --- | --- |
| Yetkazilganlar ulushi | Dashboard: «Yetkazilgan %» | O‘sadi |
| Yaratilishdan topshirishgacha o‘rtacha vaqt | Dashboard: «O‘rtacha yetkazish» | Kamayadi |
| Eng sekin bosqich | Dashboard: «Bosqich vaqti» | Aniqlanadi va tuzatiladi |
| Bekor qilinganlar ulushi | Dashboard: «Holatlar» → Bekor | Sabablari tahlil qilinadi |
| «Posilkam qayerda?» qo‘ng‘iroqlari | Operator hisobi | Havola tufayli kamayadi |

## Keyingi bosqich (roadmap)

1. **Mijozga SMS** — buyurtma yaratilganda va yo‘lga chiqqanda kuzatuv havolasi bilan
   (Eskiz.uz yoki Play Mobile; hodisalar allaqachon RabbitMQ’da — yangi `notification-service` tinglaydi).
2. **SLA** — «Yo‘lda» holatida 3 soatdan ortiq turgan buyurtmalar ro‘yxat boshida qizil belgida.
3. **Topshirish isboti** — qabul qiluvchi ismi yoki rasm, kuryer ekranida.
4. **Kuryer yuklamasi bo‘yicha avtomatik taklif** — biriktirishda eng kam band kuryer birinchi.
