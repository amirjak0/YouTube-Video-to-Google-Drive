import os
import logging
import yt_dlp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TRACKING_FILE = 'downloaded_videos.txt'
DOWNLOAD_FOLDER = 'downloads'

def setup_environment():
    # ساخت پوشه دانلود و فایل ذخیره شناسه‌ها اگر وجود نداشته باشند
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)
    if not os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'w') as f:
            pass

def get_downloaded_ids():
    # خواندن لیست ویدیوهایی که قبلا دانلود شده‌اند
    with open(TRACKING_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_downloaded_id(video_id):
    # ذخیره شناسه ویدیوی جدید در فایل
    with open(TRACKING_FILE, 'a') as f:
        f.write(f"{video_id}\n")

def upload_to_gdrive(file_path):
    # دریافت اطلاعات ورود به گوگل درایو
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    if not all([client_id, client_secret, refresh_token, folder_id]):
        logging.warning("اطلاعات گوگل درایو یافت نشد.")
        return False

    logging.info(f"در حال آپلود: {os.path.basename(file_path)}")
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

        file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"آپلود موفق! شناسه فایل در درایو: {file.get('id')}")
        return True
    except Exception as e:
        logging.error(f"خطا در آپلود: {e}")
        return False

def process_playlist():
    # دریافت لینک لیست پخش
    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL")
    if not playlist_url:
        logging.error("لینک لیست پخش یافت نشد.")
        return

    downloaded_ids = get_downloaded_ids()

    # تنظیمات اولیه برای خواندن لیست پخش
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True
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
            if video_id in downloaded_ids:
                logging.info(f"ویدیو تکراری است و رد شد: {video_id}")
                continue

            logging.info(f"در حال دانلود ویدیوی جدید: {video_id}")
            
            # تنظیمات برای دانلود ویدیو با بهترین کیفیت
            download_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
                'merge_output_format': 'mp4',
            }
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as dl:
                    info = dl.extract_info(video.get('url') or video_id, download=True)
                    file_path = dl.prepare_filename(info)
                    
                    # اگر آپلود موفق بود، شناسه را ذخیره کن و فایل را پاک کن
                    if upload_to_gdrive(file_path):
                        save_downloaded_id(video_id)
                        os.remove(file_path)
                        logging.info("فایل از روی سرور پاک شد تا فضا اشغال نشود.")
            except Exception as e:
                logging.error(f"خطا در پردازش ویدیو {video_id}: {e}")

if __name__ == "__main__":
    setup_environment()
    process_playlist()
