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
#    راه حل: استفاده از فایل کوکی صادر شده از مرورگر واقعی کاربر.
#
# ۴. خطای نام فایل کوکی: هماهنگ‌سازی نام فایل کوکی با فایلی که در مخزن آپلود شده است.
#
# ۵. خطای 403 Forbidden: یوتیوب کلاینت‌های web و android را روی سرورهای ابری مسدود می‌کند.
#    راه حل: اضافه کردن کلاینت tv (تلویزیون هوشمند) به تنظیمات yt-dlp.
#
# ۶. چالش جاوااسکریپت (EJS): یوتیوب برای دانلود ویدیوها چالش n-parameter قرار داده که نیاز به موتور JS دارد.
#    راه حل نهایی: نصب نسخه "yt-dlp[default]" و اجبار برنامه به استفاده از Node.js.
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
# نام فایل کوکی دقیقاً مطابق با فایلی که در گیت‌هاب آپلود کرده‌اید تنظیم شد
COOKIE_FILE = 'cookies.txt' 

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

    if not os.path.exists(COOKIE_FILE):
        logging.warning(f"فایل کوکی با نام {COOKIE_FILE} یافت نشد! ممکن است با خطای 403 مواجه شوید.")

    # تنظیمات اولیه برای خواندن لیست پخش
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
        'js_runtimes': {'node': {}},
        # اضافه شدن کلاینت tv برای دور زدن خطای 403
        'extractor_args': {'youtube': ['player_client=tv,android,web']}
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logging.info("در حال دریافت اطلاعات لیست پخش...")
        try:
            playlist_dict = ydl.extract_info(playlist_url, download=False)
        except Exception as e:
            logging.error(f"خطا در دریافت اطلاعات لیست پخش: {e}")
            return
        
        if not playlist_dict or 'entries' not in playlist_dict:
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
            
            # تنظیمات برای دانلود ویدیو
            download_opts = {
                'format': 'bestvideo[vcodec!*=av01]+bestaudio/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s [{video_id}].%(ext)s',
                'merge_output_format': 'mkv',
                'cookiefile': COOKIE_FILE if os.path.exists(COOKIE_FILE) else None,
                'js_runtimes': {'node': {}},
                # اضافه شدن کلاینت tv برای دور زدن خطای 403
                'extractor_args': {'youtube': ['player_client=tv,android,web']},
                'sleep_interval': 5,
                'max_sleep_interval': 15, # افزایش زمان استراحت برای جلوگیری از بلاک شدن
                'ignoreerrors': True # رد شدن از ویدیوهای مشکل‌دار (مثل Premiere) تا کل برنامه متوقف نشود
            }
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as dl:
                    info = dl.extract_info(video.get('url') or video_id, download=True)
                    
                    # اگر ویدیو Premiere باشد یا در دسترس نباشد، info مقدار None برمی‌گرداند
                    if info is None:
                        logging.warning(f"امکان دانلود ویدیو {video_id} وجود ندارد (احتمالاً Premiere یا محدودیت سنی است).")
                        continue

                    file_path = dl.prepare_filename(info)
                    
                    # بررسی مسیر فایل (گاهی اوقات به دلیل merge شدن، پسوند فایل تغییر می‌کند)
                    if not os.path.exists(file_path):
                        base_path = os.path.splitext(file_path)[0]
                        file_path = base_path + '.mkv'

                    if os.path.exists(file_path):
                        # اگر آپلود موفق بود، فایل را پاک کن
                        if upload_to_gdrive(service, folder_id, file_path):
                            os.remove(file_path)
                            logging.info("فایل از روی سرور پاک شد تا فضا اشغال نشود.")
                    else:
                        logging.error(f"فایل دانلود شده یافت نشد: {file_path}")

            except Exception as e:
                logging.error(f"خطا در پردازش ویدیو {video_id}: {e}")

if __name__ == "__main__":
    setup_environment()
    process_playlist()
