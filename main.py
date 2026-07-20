# ==============================================================================
# 📝 یادداشت‌های فنی و تاریخچه آزمون و خطاها (برای برنامه‌نویسان آینده):
# ------------------------------------------------------------------------------
# ۱. مشکل Watch Later: این لیست پخش خصوصی است و برنامه بدون اهراز هویت سنگین به آن دسترسی ندارد.
#    راه حل: استفاده از یک لیست پخش عمومی یا Unlisted.
#
# ۲. مشکل GitHub Actions & State: فایل downloaded_videos.txt بعد از اتمام هر اجرای گیت‌هاب حذف می‌شد.
#    راه حل: بررسی مستقیم داخل پوشه Google Drive برای پیدا کردن فایل‌ها بر اساس شناسه (video_id).
#
# ۳. مسدودسازی آی‌پی‌های گیت‌هاب توسط گوگل: سرورهای گیت‌هاب به دلیل حجم درخواست بالا بلاک می‌شوند (خطای bot).
#    راه حل: استفاده از فایل cookies.txt صادر شده از مرورگر واقعی کاربر.
#
# ۴. خطای نام فایل کوکی: فایل کوکی در ویندوز به صورت cookies.txt.txt ذخیره شده بود که برنامه آن را پیدا نمی‌کرد.
#    راه حل: اصلاح نام فایل به cookies.txt در مخزن گیت‌هاب.
#
# ۵. تله کلاینت ios: شبیه‌سازی کلاینت ios اگرچه برخی چالش‌ها را دور می‌زند، اما کوکی‌ها را کاملاً نادیده می‌گیرد.
#    راه حل: استفاده از کلاینت‌های android, web, mweb که با کوکی‌ها سازگار هستند.
#
# ۶. چالش جاوااسکریپت (EJS): یوتیوب برای دانلود ویدیوها چالش n-parameter قرار داده که نیاز به موتور JS دارد.
#    موتور Deno به طور پیش‌فرض توسط yt-dlp استفاده می‌شود اما در گیت‌هاب اکشنز به درستی در PATH قرار نمی‌گیرد.
#    راه حل نهایی: نصب نسخه "yt-dlp[default]" و اجبار برنامه به استفاده از Node.js (که پیش‌فرض در گیت‌هاب نصب است)
#    از طریق تنظیم کردن پارامتر 'js_runtimes': {'node': {}} در تنظیمات دانلود.
# ==============================================================================

import os
import logging
import mimetypes
import yt_dlp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_FOLDER = 'downloads'

def setup_environment():
    # ساخت پوشه دانلود اگر وجود نداشته باشد
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

def get_gdrive_service():
    # دریافت اطلاعات ورود به گوگل درایو
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        logging.warning("اطلاعات گوگل درایو یافت نشد.")
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        creds.refresh(Request())
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"خطا در اتصال به گوگل درایو: {e}")
        return None

def video_exists_in_gdrive(service, folder_id, video_id):
    # بررسی وجود ویدیو در گوگل درایو بر اساس شناسه
    try:
        query = f"'{folder_id}' in parents and name contains '{video_id}' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        return len(items) > 0
    except Exception as e:
        logging.error(f"خطا در جستجوی فایل در درایو: {e}")
        return False

def upload_to_gdrive(service, folder_id, file_path):
    logging.info(f"در حال آپلود: {os.path.basename(file_path)}")
    try:
        file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
        
        # تشخیص خودکار نوع فایل (mkv, mp4 و غیره) برای آپلود صحیح در درایو
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
            
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"آپلود موفق! شناسه فایل در درایو: {file.get('id')}")
        return True
    except Exception as e:
        logging.error(f"خطا در آپلود: {e}")
        return False

def process_playlist():
    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    if not playlist_url or not folder_id:
        logging.error("لینک لیست پخش یا شناسه پوشه یافت نشد.")
        return

    service = get_gdrive_service()
    if not service:
        return

    # تنظیمات اولیه برای خواندن لیست پخش (استفاده از کوکی‌ها و فعال کردن موتور Node.js گیت‌هاب)
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'cookiefile': 'cookies.txt',
        'js_runtimes': {'node': {}},
        'extractor_args': {'youtube': ['player_client=android,web,mweb']}
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logging.info("در حال دریافت اطلاعات لیست پخش...")
        playlist_dict = ydl.extract_info(playlist_url, download=False)
        
        if 'entries' not in playlist_dict:
            logging.error("ویدیویی یافت نشد.")
            return

        for video in playlist_dict['entries']:
            if not video:
                continue
            
            video_id = video.get('id')
            
            # بررسی اینکه آیا ویدیو قبلا در درایو آپلود شده است یا خیر
            if video_exists_in_gdrive(service, folder_id, video_id):
                logging.info(f"ویدیو از قبل در درایو موجود است و رد شد: {video_id}")
                continue

            logging.info(f"در حال دانلود ویدیوی جدید: {video_id}")
            
            # تنظیمات برای دانلود ویدیو (4K روان بدون کدک AV1)
            download_opts = {
                'format': 'bestvideo[vcodec!*=av01]+bestaudio/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s [{video_id}].%(ext)s',
                'merge_output_format': 'mkv',
                'cookiefile': 'cookies.txt',
                'js_runtimes': {'node': {}},
                'extractor_args': {'youtube': ['player_client=android,web,mweb']},
                'sleep_interval': 5,
                'max_sleep_interval': 10
            }
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as dl:
                    info = dl.extract_info(video.get('url') or video_id, download=True)
                    file_path = dl.prepare_filename(info)
                    
                    # اگر آپلود موفق بود، فایل را پاک کن
                    if upload_to_gdrive(service, folder_id, file_path):
                        os.remove(file_path)
                        logging.info("فایل از روی سرور پاک شد تا فضا اشغال نشود.")
            except Exception as e:
                logging.error(f"خطا در پردازش ویدیو {video_id}: {e}")

if __name__ == "__main__":
    setup_environment()
    process_playlist()
