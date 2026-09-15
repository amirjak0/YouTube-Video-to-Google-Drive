import os
import sys
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
import yt_dlp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

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

def yt_dlp_common_args(cookies_path: Optional[str]) -> List[str]:
    args = []
    if cookies_path and os.path.exists(cookies_path):
        args.extend(["--cookies", cookies_path])
    return args

def probe_best_format(video_url: str, cookies_path: Optional[str] = None) -> Tuple[Optional[str], int, Optional[str]]:
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-warnings",
    ]
    cmd.extend(yt_dlp_common_args(cookies_path))
    cmd.append(video_url)

    best_height = 0
    best_format_id = None
    chosen_client = "default"

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            import json
            info = json.loads(res.stdout)
            for f in info.get("formats", []):
                h = f.get("height")
                if h and h > best_height and f.get("vcodec") != "none":
                    best_height = h
                    best_format_id = f.get("format_id")
            return best_format_id, best_height, chosen_client
    except Exception as e:
        logger.warning(f"Default probe failed: {e}")

    logger.warning("Default extraction failed or yielded no resolution; falling back to alternative client options.")
    for client in ["web", "mweb", "android"]:
        alt_cmd = cmd.copy()
        alt_cmd.extend(["--extractor-args", f"youtube:player_client={client}"])
        try:
            res = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                import json
                info = json.loads(res.stdout)
                for f in info.get("formats", []):
                    h = f.get("height")
                    if h and h > best_height and f.get("vcodec") != "none":
                        best_height = h
                        best_format_id = f.get("format_id")
                if best_height > 0:
                    return best_format_id, best_height, client
        except Exception:
            pass

    return None, 0, None

def verify_file_resolution(file_path: Path) -> int:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=height",
        "-of", "csv=s=x:p=0",
        str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0 and res.stdout.strip().isdigit():
            return int(res.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe check failed for {file_path.name}: {e}")
    return 0

def download_video(video_url: str, target_client: str = "web", cookies_path: Optional[str] = None, max_resolution: int = 2160) -> Optional[Tuple[Path, int]]:
    for f in DOWNLOADS_DIR.glob("*.mkv"):
        try:
            f.unlink()
        except Exception:
            pass

    output_template = str(DOWNLOADS_DIR / "%(title)s [%(id)s] [%(height)sp].%(ext)s")
    
    clients = [target_client]
    if target_client != "default":
        clients.append("default")
        
    for client in clients:
        cmd = [
            "yt-dlp",
            "-f", f"bestvideo[height<={max_resolution}]+bestaudio/best[height<={max_resolution}]",
            "--merge-output-format", "mkv",
            "--extractor-args", f"youtube:player_client={client}",
            "-o", output_template,
            "--embed-metadata",
            "--no-mtime",
            "--retries", "3",
            "--fragment-retries", "3",
        ]
        cmd.extend(yt_dlp_common_args(cookies_path))
        cmd.append(video_url)

        logger.info(f"Attempting download via client '{client}'...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.warning(f"Client '{client}' failed (code {res.returncode}): {(res.stderr or res.stdout)[-700:]}")
            continue

        downloaded_files = [f for f in DOWNLOADS_DIR.glob("*.mkv") if f.is_file()]
        if not downloaded_files:
            continue

        latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
        actual_height = verify_file_resolution(latest_file)
        if actual_height <= 0:
            continue

        logger.info(f"Successfully downloaded: {latest_file.name} (verified {actual_height}p)")
        return latest_file, actual_height

    return None

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

def process_single_video(
    video_url: str,
    gdrive_service,
    folder_id: str,
    existing_drive_files: Dict[str, Dict[str, Any]],
    update_existing: bool = True,
    cookies_path: Optional[str] = None,
    force_quality_limit: int = 2160
):
    logger.info(f"\n=======================================================")
    logger.info(f"Processing video: {video_url}")

    id_match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", video_url)
    video_id = id_match.group(1) if id_match else None

    best_format_id, available_height, chosen_client = probe_best_format(video_url, cookies_path)
    if not chosen_client or available_height <= 0:
        logger.error(f"No downloadable video formats found for {video_url}.")
        return False

    logger.info(f"Highest downloadable resolution available online: {available_height}p (via {chosen_client})")

    existing_entry = existing_drive_files.get(video_id) if video_id else None
    old_file_id = None

    if existing_entry:
        existing_height = existing_entry.get("height", 0)
        old_file_id = existing_entry.get("file_id")
        old_name = existing_entry.get("name")
        
        logger.info(f"Found existing file in Drive: '{old_name}' (Detected resolution: {existing_height}p)")
        if existing_height >= available_height and not os.environ.get("FORCE_RETRY"):
            logger.info(f"Video {video_id} is already in Drive at max resolution. Skipping.")
            return True
            
        if update_existing and available_height > existing_height:
            logger.info(f">>> [AUTO-UPGRADE] Upgrading video {video_id} from {existing_height}p to {available_height}p! <<<")
        else:
            logger.info(f"Update existing is disabled. Skipping {video_id}.")
            return True

    download_res = download_video(
        video_url,
        target_client=chosen_client,
        cookies_path=cookies_path,
        max_resolution=min(force_quality_limit, max(available_height, 1080))
    )

    if not download_res:
        logger.error(f"Failed to download high-resolution stream for {video_url}.")
        return False

    downloaded_file, verified_height = download_res
    uploaded_id = upload_to_drive(gdrive_service, downloaded_file, folder_id, old_file_id=old_file_id)
    
    if uploaded_id:
        logger.info(f"SUCCESS: Video {video_id or ''} synced to Google Drive at {verified_height}p!")
        try:
            downloaded_file.unlink()
        except Exception:
            pass
        return True

    return False

def get_playlist_videos(playlist_url: str, cookies_path: Optional[str] = None) -> List[str]:
    if "list=" not in playlist_url:
        return [playlist_url]

    logger.info(f"Extracting video list from playlist: {playlist_url}...")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "webpage_url",
        "--no-warnings",
        "--extractor-args", "youtube:player_client=web",
    ]
    cmd.extend(yt_dlp_common_args(cookies_path))
    cmd.append(playlist_url)

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:
        logger.error(f"Failed to execute playlist extraction: {e}")
        return []

    if res.returncode != 0:
        logger.error(f"Playlist extraction failed: {res.stderr[-1000:]}")
        return []

    urls = [line.strip() for line in res.stdout.splitlines() if line.strip().startswith(("http://", "https://"))]
    logger.info(f"Found {len(urls)} videos in playlist.")
    return urls

def main():
    print("================================================================")
    print("YouTube Video to Google Drive - High Quality Auto-Updater & Sync")
    print("================================================================")

    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL") or os.environ.get("YOUTUBE_VIDEO_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID", "")
    update_existing = os.environ.get("UPDATE_EXISTING", "true").lower() in ("true", "1", "yes")
    cookies_content = os.environ.get("YOUTUBE_COOKIES")

    if not playlist_url:
        logger.error("Error: YOUTUBE_PLAYLIST_URL or YOUTUBE_VIDEO_URL environment variable is required.")
        sys.exit(1)

    cookies_path = None
    if cookies_content and len(cookies_content.strip()) > 10:
        cookies_path = "youtube_cookies.txt"
        with open(cookies_path, "w", encoding="utf-8") as f:
            f.write(cookies_content)
        logger.info("Loaded YouTube authentication cookies from environment.")

    service = get_gdrive_service()
    existing_drive_files = scan_drive_folder(service, folder_id) if (service and folder_id) else {}
    
    force_quality_limit = int(os.environ.get("FORCE_QUALITY_LIMIT", "2160") or "2160")
    force_quality_limit = max(360, min(force_quality_limit, 2160))

    video_urls = get_playlist_videos(playlist_url, cookies_path)
    if not video_urls:
        logger.error("No videos were extracted.")
        sys.exit(1)

    success_count = 0
    for idx, video_url in enumerate(video_urls, 1):
        logger.info(f"\nProcessing [{idx}/{len(video_urls)}]: {video_url}")
        try:
            if process_single_video(
                video_url=video_url,
                gdrive_service=service,
                folder_id=folder_id,
                existing_drive_files=existing_drive_files,
                update_existing=update_existing,
                cookies_path=cookies_path,
                force_quality_limit=force_quality_limit
            ):
                success_count += 1
        except Exception as err:
            logger.error(f"An unexpected error occurred for {video_url}: {err}")

    if success_count == 0:
        logger.error("No video was successfully synchronized.")
        sys.exit(1)

    logger.info(f"Successfully synchronized {success_count}/{len(video_urls)} video(s).")

    if cookies_path and os.path.exists(cookies_path):
        try:
            os.remove(cookies_path)
        except Exception:
            pass

if __name__ == "__main__":
    main()
