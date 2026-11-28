# Interfeys dizayni

`gateway/demo/index.html` — bitta HTML fayl, tashqi kutubxona va shriftsiz (gateway CSP’si
faqat o‘z manbalariga ruxsat beradi, sahifa internetsiz ham ishlaydi).

**Uslub:** «soft UI» — TBC, Click, Payme kabi o‘zbek fintech ilovalarining sokin, yumaloq
ko‘rinishi. Kulrang fon ustida oq kartalar, chegara chiziqlari o‘rniga yumshoq soya, katta radiuslar.

## UI/UX tamoyillari

| # | Tamoyil | Interfeysda qanday |
| --- | --- | --- |
| 1 | **Bitta ekran — bitta asosiy harakat** | Har ekranda faqat bitta ko‘k tugma: «Yaratish», «Omborga qabul qilish», «Kuzatish». Ikkinchi darajalilari och fonli |
| 2 | **Xatoning oldini olish** (Nielsen #5) | Buyurtma kartasida faqat **keyingi** qadam tugmasi. Bosqichni o‘tkazib yuboradigan tugma umuman yo‘q |
| 3 | **Tizim holati ko‘rinib turadi** (#1) | Marshrut (4 bekat), holat belgilari, tugmada yuklanish aylanasi, har amaldan keyin toast |
| 4 | **Kamroq matn, bosqichma-bosqich ochish** | Tushuntirish matnlari olib tashlandi. Tafsilot kerak bo‘lsa — yashirin: grafik ostida «Jadval», jurnalda JSON, tugunlarda tooltip |
| 5 | **Eslab qolish emas, tanib olish** (#6) | Kirishda namoyish hisoblari tugma sifatida, so‘nggi buyurtmalar ro‘yxati — kodni yozish shart emas |
| 6 | **Izchillik** (#4) | Holat ranglari hamma joyda bir xil; bitta ikon uslubi; bitta radius va soya shkalasi |
| 7 | **Aniq xato xabari** (#9) | Xato nima bo‘lganini va nima qilishni aytadi: «Avval buyurtmaga kuryer biriktiring.» |
| 8 | **Rolga qarab interfeys** | Menyu rolga mos: kuryer faqat o‘z yetkazmalarini ko‘radi, admin — foydalanuvchilarni. Ruxsatni baribir server tekshiradi |
| 9 | **Fitts qonuni** | Tugma va maydonlar 48 px, menyu bandlari 46 px — barmoq bilan ham oson bosiladi |
| 10 | **Bo‘sh holat — keyingi qadam** | Ikon + bir qator: «Buyurtma tanlanmagan — yangisini yarating yoki ro‘yxatdan tanlang» |

## Tokenlar

| Token | Qiymat | Vazifa |
| --- | --- | --- |
| `--canvas` | `#EEF2F7` | Fon: ko‘kish sovuq kulrang (brendga mos) |
| `--surface` | `#FFFFFF` | Kartalar |
| `--sunken` | `#F4F6FA` | Maydonlar, ikkinchi darajali tugmalar |
| `--ink` / `--ink-2` | `#172036` / `#5A6478` | Matn: qora emas, brend tusli to‘q ko‘k |
| `--brand` | `#2C62DE` | Faqat asosiy harakat va faol holat |
| Radius | 14 maydon · 16 tugma · 22 karta · 999 belgi | Katta, darajali |
| Soya | `0 12px 32px -16px` ink rangida, past shaffoflik | Kartalar chiziqsiz «suzadi» |

**Holat ranglari** (matn / fon) — hamma joyda bir xil:

| Yangi | Omborda | Yo‘lda | Yetkazildi |
| --- | --- | --- | --- |
| `#4B5568` / `#EEF1F5` | `#94600A` / `#FFF3DC` | `#2453C4` / `#E8EEFF` | `#12784A` / `#E3F6EC` |

**Kontrast (WCAG AA, hisoblangan):** oq/brend 5,37 · asosiy matn 14,4 · ikkinchi darajali matn
5,3–6,0 · holat belgilari 4,85–6,6. Hammasi ≥ 4,5.

## Komponentlar

- **Tugmalar:** asosiy — ko‘k, rangli soyali; yumshoq — och ko‘k fon («Biriktirish»);
  neytral — kulrang («Namoyish hisoblarini qo‘shish»). Qora tugma yo‘q. Bosilganda 2% kichrayadi,
  yuklanishda aylana chiqadi va ikki marta bosib bo‘lmaydi.
- **Maydonlar:** chegarasiz kulrang fon; fokusda oq fon + ko‘k halqa. Yorliq har doim maydon ustida.
- **Ro‘yxatlar:** bitta oq karta ichida ingichka ajratgichlar (har qatorga alohida karta emas).
- **Toast:** natija xabari ekran pastida, 3 s (xato — 5 s), bir vaqtda ko‘pi bilan 2 ta. Sahifa
  ichidagi qizil-yashil xabar bloklari olib tashlandi — matn kamaydi.
- **Navigatsiya:** chapda ikonli menyu; faol band oq karta. Telefonda yuqorida gorizontal suriladi.

## Ekranlar

| Ekran | Tuzilish |
| --- | --- |
| Kirish | Markazda bitta karta; namoyish hisoblari — kichik tugmalar |
| Buyurtmalar | Chapda: yangi buyurtma + tanlangan buyurtma (marshrut va keyingi qadam). O‘ngda: so‘nggi buyurtmalar |
| Dashboard | 4 ta ko‘rsatkich kartasi + 4 ta grafik (holatlar, 24 soat, bosqich vaqti, kuryerlar) |
| Kuzatish | Kod → holat va vaqt chizig‘i. Token kerak emas |
| Jurnal | Gateway orqali o‘tgan har bir so‘rov: status kodi, nomi, JSON (yashirin) |

## Grafiklar

- SVG, kutubxonasiz. Bar — yumaloq, kulrang «yo‘lak» ustida; qiymat o‘ngda; o‘q chiziqlari minimal.
- Har grafikda tooltip (sichqoncha va Tab) va «Jadval» ko‘rinishi — rangni ko‘rmaydiganlar uchun.
- Ikki o‘qli grafik yo‘q. Matn hech qachon ma’lumot rangida emas.
- Palitra rang ko‘rish nuqsoni simulyatsiyasi bilan tekshirildi: qo‘shni juftliklar ΔE ≥ 13.
  «Yangi» ataylab neytral kulrang — har bar nomi bilan yozilgan, rang yagona belgi emas.

Tizim arxitekturasi interfeysda emas, hujjatda: [architecture.md](architecture.md).

## Texnik

- Token faqat sahifa xotirasida; 15 daqiqada tugasa refresh bilan jimgina yangilanadi.
- Server ma’lumoti HTML’ga `esc()` orqali (XSS himoyasi). Gateway qat’iy CSP qo‘yadi.
- Klaviatura: barcha boshqaruvlarda ko‘rinadigan fokus halqasi. `prefers-reduced-motion` — animatsiyasiz.
- 390 px dan 1440 px gacha gorizontal siljishsiz (avtomatik tekshirilgan).

## Tekshiruv

Chrome (Playwright): har bir rol bo‘yicha to‘liq ssenariy, dashboard, kuzatish,
jurnal, telefon (390 px). JavaScript xatosi yo‘q, sahifa kengligi ekrandan oshmaydi.
