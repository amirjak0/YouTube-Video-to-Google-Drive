import os
import sys
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

# کتابخانه‌های جدید برای کوکی
from playwright.sync_api import sync_playwright
import yt_dlp

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------
# تابع جدید: دریافت کوکی با Playwright 
# ---------------------------------------------------------
def generate_youtube_cookies(output_file="youtube_cookies.txt"):
    logger.info("🚀 Starting Chrome to generate YouTube cookies...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            page.goto("https://www.youtube.com")
            
            logger.info("⏳ Waiting for cookies to settle and bypassing bot detection...")
            page.wait_for_timeout(5000) 
            
            cookies = context.cookies()
            
            with open(output_file, "w") as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in cookies:
                    domain = cookie['domain']
                    include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
                    path = cookie['path']
                    secure = 'TRUE' if cookie['secure'] else 'FALSE'
                    expires = int(cookie['expires']) if 'expires' in cookie and cookie['expires'] > 0 else 0
                    name = cookie['name']
                    value = cookie['value']
                    f.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
            
            browser.close()
            logger.info(f"✅ Cookies successfully saved to {output_file}")
            return output_file
    except Exception as e:
        logger.error(f"❌ Failed to generate cookies: {e}")
        return None

# ---------------------------------------------------------
# توابع گوگل درایو (بدون تغییر)
# ---------------------------------------------------------
def get_gdrive_service():
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logger.error("Missing Google Drive credentials.")
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build('drive', 'v3', credentials=creds)

def scan_drive_folder(service, folder_id: str) -> Dict[str, Dict[str, Any]]:
    existing_files = {}
    query = f"'{folder_id}' in parents and trashed=false"
    try:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            pageSize=1000
        ).execute()
        items = results.get("files", [])
        for item in items:
            name = item.get("name", "")
            id_match = re.search(r"\[([a-zA-Z0-9_-]{11})\]", name)
            if id_match:
                vid_id = id_match.group(1)
                height_match = re.search(r"(\d{3,4})p", name)
                height = int(height_match.group(1)) if height_match else 0
                if vid_id not in existing_files or height > existing_files[vid_id]["height"]:
                    existing_files[vid_id] = {
                        "file_id": item.get("id"),
                        "name": name,
                        "height": height
                    }
        return existing_files
    except Exception as e:
        logger.error(f"Failed to scan Google Drive folder: {e}")
        return {}

def upload_to_drive(service, file_path: Path, folder_id: str, old_file_id: Optional[str] = None) -> Optional[str]:
    file_metadata = {'name': file_path.name}
    if not old_file_id and folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(str(file_path), resumable=True)
    try:
        if old_file_id:
            logger.info(f"Updating existing file on Drive (ID: {old_file_id})")
            updated_file = service.files().update(
                fileId=old_file_id,
                media_body=media
            ).execute()
            return updated_file.get("id")
        else:
            logger.info("Uploading new file to Drive...")
            created_file = service.files().create(
                body=file_metadata,
                media_body=media
            ).execute()
            return created_file.get("id")
    except Exception as e:
        logger.error(f"Google Drive upload failed: {e}")
        return None

# ---------------------------------------------------------
# توابع دانلود یوتوب (اصلاح شده برای استفاده از کوکی اتوماتیک)
# ---------------------------------------------------------
def yt_dlp_common_args(cookies_path: Optional[str]) -> List[str]:
    args = []
    if cookies_path and os.path.exists(cookies_path):
        args.extend(["--cookies", cookies_path])
    return args

def download_video(video_url: str, cookies_path: Optional[str] = None):
    output_template = str(DOWNLOADS_DIR / "%(title)s [%(id)s] [%(height)sp].%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mkv',
        'retries': 3,
        'cookiefile': cookies_path, # استفاده از کوکی
    }
    
    logger.info(f"Attempting download for {video_url}...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info_dict)
            # جایگزین کردن ext با mkv به دلیل merge
            filename = os.path.splitext(filename)[0] + '.mkv'
            return Path(filename), info_dict.get('height', 0)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None, 0

def process_single_video(video_url: str, gdrive_service, folder_id: str, existing_drive_files: Dict, cookies_path: str):
    logger.info(f"Processing video: {video_url}")
    
    id_match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", video_url)
    video_id = id_match.group(1) if id_match else None
    
    # 1. دانلود ویدیو با استفاده از کوکی‌ها
    res = download_video(video_url, cookies_path=cookies_path)
    if not res[0]:
        return False
        
    downloaded_file, verified_height = res
    existing_entry = existing_drive_files.get(video_id) if video_id else None
    old_file_id = None
    
    if existing_entry:
        if existing_entry.get("height", 0) >= verified_height:
            logger.info("Video already in Drive at max resolution. Skipping upload.")
            downloaded_file.unlink()
            return True
        old_file_id = existing_entry.get("file_id")

    # 2. آپلود در درایو
    uploaded_id = upload_to_drive(gdrive_service, downloaded_file, folder_id, old_file_id=old_file_id)
    if uploaded_id:
        logger.info(f"SUCCESS: Video {video_id or ''} synced to Google Drive!")
        try:
            downloaded_file.unlink()
        except Exception:
            pass
        return True
    return False

def main():
    print("================================================================")
    print("YouTube Video to Google Drive - High Quality Auto-Updater & Sync")
    print("================================================================")
    
    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL") or os.environ.get("YOUTUBE_VIDEO_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID", "")
    
    if not playlist_url:
        logger.error("Error: YOUTUBE_PLAYLIST_URL or YOUTUBE_VIDEO_URL environment variable is required.")
        sys.exit(1)
        
    # **دریافت اتوماتیک کوکی‌ها در ابتدای کار**
    cookies_path = generate_youtube_cookies()
    if not cookies_path:
        logger.error("Failed to get cookies. Proceeding without them (may fail on age-restricted or blocked videos).")

    service = get_gdrive_service()
    existing_drive_files = scan_drive_folder(service, folder_id) if (service and folder_id) else {}

    # اجرای پروسه برای ویدیو
    # اگر پلی‌لیست باشد، باید متد extract_playlist اضافه شود، اما برای لینک تکی مستقیماً پردازش می‌کنیم:
    process_single_video(
        video_url=playlist_url,
        gdrive_service=service,
        folder_id=folder_id,
        existing_drive_files=existing_drive_files,
        cookies_path=cookies_path
    )
    
    # حذف کوکی بعد از اتمام کار برای امنیت
    if cookies_path and os.path.exists(cookies_path):
        os.remove(cookies_path)

if __name__ == "__main__":
    main()
