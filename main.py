import os
import logging
import yt_dlp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_FOLDER = 'downloads'

def setup_environment():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

def get_gdrive_service():
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
        media = MediaFileUpload(file_path, mimetype='video/mp4', resumable=True)
        
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

    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'extractor_args': {'youtube': ['player_client=ios']}
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
            
            if video_exists_in_gdrive(service, folder_id, video_id):
                logging.info(f"ویدیو از قبل در درایو موجود است و رد شد: {video_id}")
                continue

            logging.info(f"در حال دانلود ویدیوی جدید: {video_id}")
            
            download_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s [{video_id}].%(ext)s',
                'merge_output_format': 'mp4',
                'extractor_args': {'youtube': ['player_client=ios']},
                'sleep_interval': 5,
                'max_sleep_interval': 10
            }
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as dl:
                    info = dl.extract_info(video.get('url') or video_id, download=True)
                    file_path = dl.prepare_filename(info)
                    
                    if upload_to_gdrive(service, folder_id, file_path):
                        os.remove(file_path)
                        logging.info("فایل از روی سرور پاک شد تا فضا اشغال نشود.")
            except Exception as e:
                logging.error(f"خطا در پردازش ویدیو {video_id}: {e}")

if __name__ == "__main__":
    setup_environment()
    process_playlist()
