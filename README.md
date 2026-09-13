# 📥 YouTube → Google Drive

این پروژه ویدیوهای یک Playlist یوتیوب را با GitHub Actions دانلود و به Google Drive منتقل می‌کند.

## ویژگی‌ها

- اجرای خودکار هر ۶ ساعت و همچنین اجرای دستی از GitHub Actions
- انتخاب **بالاترین کیفیت واقعاً قابل دانلود برای هر ویدیو**؛ بدون فرض ثابت 360p/720p/1080p/4K
- بررسی چند YouTube player client برای پیدا کردن بیشترین کیفیت قابل استفاده در همان اجرای فعلی
- دانلود جداگانه بهترین Video و Audio و ادغام با FFmpeg
- بررسی رزولوشن فایل نهایی با `ffprobe`
- اگر یک فرمت باکیفیت‌تر قابل دانلود نباشد، سیستم فرمت بعدی را امتحان می‌کند
- استفاده از Cookieهای YouTube و PO Token Provider برای دسترسی پایدارتر
- حذف فایل قدیمی با کیفیت پایین بعد از آپلود موفق نسخه جدید
- حذف فایل موقت از Runner بعد از آپلود موفق
- جلوگیری از دانلود تکراری با بررسی Google Drive

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

برای هر ویدیو، `main.py` به جای انتخاب کورکورانه یک format ثابت، Clientهای مختلف یوتیوب را Probe می‌کند و فقط Formatهایی را در نظر می‌گیرد که URL واقعی قابل دانلود دارند.

ترتیب کیفیت بر اساس رزولوشن و سپس FPS و Bitrate مقایسه می‌شود:

```text
2160p > 1440p > 1080p > 720p > 480p > 360p
```

پس اگر ویدیویی فقط 720p داشته باشد، 720p دانلود می‌شود. اگر 1080p داشته باشد، 1080p و اگر 4K قابل دانلود باشد، 4K دانلود می‌شود.

نکته مهم: ممکن است YouTube یک کیفیت بالاتر را در Metadata نشان دهد اما برای آن Session URL مستقیم قابل دانلود ارائه نکند. در این حالت سیستم آن کیفیت را «قابل دانلود» حساب نمی‌کند و کیفیت پایین‌ترِ واقعاً قابل دانلود را انتخاب می‌کند.

## فایل Quality Test

`quality-test.yml` اولین ویدیوی Playlist را به صورت آزمایشی بررسی می‌کند و این موارد را گزارش می‌دهد:

- `GLOBAL_METADATA_MAX`: بالاترین کیفیت اعلام‌شده در Metadata
- `GLOBAL_DOWNLOADABLE_MAX`: بالاترین کیفیتی که URL مستقیم قابل دانلود دارد
- `FINAL REAL DOWNLOAD`: رزولوشن واقعی فایل پس از دانلود و ادغام

این تست عمداً در صورت نبودن Format مستقیم، آن را به اشتباه 360p اعلام نمی‌کند.

## نیازمندی‌ها

- Python 3.11
- Node.js 22
- FFmpeg
- `yt-dlp`
- `yt-dlp-ejs`
- `bgutil-ytdlp-pot-provider`
- Google Drive API packages

تمام وابستگی‌ها در `requirements.txt` قرار دارند و Workflow اصلی آن‌ها را نصب می‌کند.

## Secrets موردنیاز

```text
YOUTUBE_PLAYLIST_URL
YOUTUBE_COOKIES
GDRIVE_CLIENT_ID
GDRIVE_CLIENT_SECRET
GDRIVE_REFRESH_TOKEN
GDRIVE_FOLDER_ID
```

## نکات مهم

فایل `cookies.txt` و اطلاعات Google Drive نباید داخل Repository ذخیره شوند؛ این اطلاعات باید فقط در GitHub Actions Secrets باشند.

فایل‌های خروجی با شناسه ویدیو و رزولوشن ذخیره می‌شوند، برای مثال:

```text
Video Title [bYWatIh1LzQ] [1080p].mkv
```

در نتیجه کیفیت فایل خروجی از نام آن نیز قابل تشخیص است.
