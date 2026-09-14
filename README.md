# 📥 YouTube → Google Drive

این پروژه ویدیوهای یک Playlist یوتیوب را با GitHub Actions دانلود و به Google Drive منتقل می‌کند.

## ویژگی‌ها

- اجرای خودکار هر ۶ ساعت و همچنین اجرای دستی از GitHub Actions
- بررسی چند YouTube Player Client برای پیدا کردن بیشترین کیفیتی که yt-dlp در همان اجرای فعلی برای ویدیو پیدا می‌کند
- دانلود بهترین Video و Audio و ادغام آن‌ها با FFmpeg
- بررسی رزولوشن واقعی فایل نهایی با `ffprobe`
- تلاش چند مرحله‌ای برای دانلود در صورت شکست Client یا خطاهای YouTube
- استفاده از YouTube Cookies برای Clientهای وب
- استفاده از Node.js و `yt-dlp-ejs` برای JavaScript challenges
- استفاده از BgUtils PO Token Provider در Workflow
- امکان ارتقای فایل موجود در Google Drive، اگر رزولوشن بالاتری برای آن ویدیو در دسترس باشد
- حذف فایل قدیمی پس از آپلود موفق نسخه جدید
- جلوگیری از دانلود تکراری وقتی فایل موجود در Drive حداقل همان رزولوشن تشخیص‌داده‌شده را دارد

## ساختار پروژه

```text
.
├── .github/
│   └── workflows/
│       ├── run.yml
│       └── quality-test.yml
├── main.py
├── requirements.txt
└── README.md
```

## منطق انتخاب کیفیت

برای هر ویدیو، `main.py` چند Player Client یوتیوب را بررسی می‌کند:

```text
ios
android
tv
tv_simply
web_safari
mweb
web
```

فرمت‌های ویدیویی گزارش‌شده توسط هر Client بر اساس این معیارها مقایسه می‌شوند:

1. ارتفاع تصویر (Resolution)
2. عرض تصویر
3. FPS
4. Bitrate

بنابراین هدف برنامه این است که:

```text
720p موجود باشد → 720p
1080p موجود باشد → 1080p
1440p موجود باشد → 1440p
2160p / 4K موجود باشد → 4K
```

**توجه مهم:** «موجود» در اینجا به فرمت‌هایی اشاره دارد که yt-dlp برای همان Client در همان Session در اختیار برنامه قرار می‌دهد. YouTube ممکن است به دلیل Client، Session، Cookie، SABR یا محدودیت‌های دیگر، یک کیفیت بالاتر را ارائه نکند.

### رفتار فعلی Probe

تابع `probe_best_format()` Clientها را به ترتیب بالا بررسی می‌کند. وقتی کیفیت 1080p یا بالاتر پیدا شود، Probe برای جلوگیری از درخواست‌های اضافه متوقف می‌شود؛ بنابراین README نباید ادعا کند که همیشه همه Clientها بررسی می‌شوند.

همچنین Probe فعلی، ارتفاع فرمت ویدیویی گزارش‌شده را مقایسه می‌کند. «قابل دانلود بودن واقعی» در مرحله دانلود با موفقیت اجرای yt-dlp و سپس بررسی فایل خروجی با `ffprobe` تأیید می‌شود.

## دانلود و Fallback

پس از انتخاب Client، برنامه چند استراتژی دانلود را امتحان می‌کند:

1. `ios,tv` بدون Cookie
2. `android` بدون Cookie
3. Client انتخاب‌شده به همراه `android` بدون Cookie
4. Client انتخاب‌شده با Cookie

فرمت دانلود:

```text
bestvideo[height<=2160]+bestaudio/bestvideo+bestaudio/best
```

و خروجی با FFmpeg در قالب MKV ادغام می‌شود.

پس از دانلود، `ffprobe` ارتفاع واقعی Video Stream را بررسی می‌کند.

## Google Drive

قبل از دانلود، فایل‌های موجود در پوشه Google Drive بررسی می‌شوند.

اگر فایل موجود حداقل همان رزولوشنی را داشته باشد که برنامه برای ویدیوی آنلاین تشخیص داده است، دانلود دوباره انجام نمی‌شود.

اگر رزولوشن بالاتری در دسترس باشد، برنامه:

1. نسخه باکیفیت‌تر را دانلود می‌کند.
2. آن را به Google Drive آپلود می‌کند.
3. پس از آپلود موفق، فایل قدیمی را حذف می‌کند.

## Quality Test

فایل:

```text
.github/workflows/quality-test.yml
```

برای آزمایش کیفیت یک ویدیوی نمونه استفاده می‌شود.

هدف آن این است که کیفیت‌های گزارش‌شده توسط Clientهای مختلف و در صورت امکان کیفیت واقعی فایل دانلودشده را با `ffprobe` بررسی کند.

خروجی تست را باید بر اساس لاگ همان اجرای Workflow تفسیر کرد؛ اجرای موفق Workflow به‌تنهایی به معنی 4K بودن خروجی نیست.

## نیازمندی‌ها

- Python 3.11
- Node.js 22
- FFmpeg
- `yt-dlp`
- `yt-dlp-ejs`
- Google Drive API packages
- BgUtils PO Token Provider برای Workflow

وابستگی‌های Python در `requirements.txt` قرار دارند.

## Secrets موردنیاز

در GitHub Actions این Secrets باید تنظیم شوند:

```text
YOUTUBE_PLAYLIST_URL
YOUTUBE_COOKIES
GDRIVE_CLIENT_ID
GDRIVE_CLIENT_SECRET
GDRIVE_REFRESH_TOKEN
GDRIVE_FOLDER_ID
```

## امنیت

فایل Cookie و اطلاعات Google Drive را داخل Repository قرار ندهید.

این اطلاعات باید فقط در GitHub Actions Secrets نگهداری شوند.

## نام فایل خروجی

نام فایل خروجی شامل عنوان، شناسه و ارتفاع تشخیص‌داده‌شده است:

```text
Video Title [VIDEO_ID] [1080p].mkv
```

ارتفاع درج‌شده در نام فایل توسط `yt-dlp` تعیین می‌شود و رزولوشن واقعی فایل پس از دانلود نیز با `ffprobe` بررسی می‌شود.
