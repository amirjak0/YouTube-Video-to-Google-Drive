#!/usr/bin/env python3
"""
YouTube Video to Google Drive - High Quality Auto-Updater & Synchronizer
========================================================================
- Bypasses SABR throttling and 360p lock using multi-client routing (ios, android, tv).
- Immune to YouTube 'The page needs to be reloaded' by isolating cookie-less mobile clients.
- Scans Google Drive for existing files:
    * If a video is already in Drive at 360p/720p and 1080p+ is available,
      it downloads the high-res version, uploads it, and purges the old lower-res copy.
    * If already at max resolution, skips redundant re-downloading.
"""

import os
import re
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import google.auth
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("yt-gdrive-sync")

# Constants & Defaults
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Candidate clients for format detection
PLAYER_CLIENT_CANDIDATES = [
    "web",
    "mweb",
    "tv",
    "android",
    "ios"
]

def yt_dlp_common_args(cookies_path: Optional[str] = None) -> List[str]:
    """Common YouTube extraction options for current yt-dlp + EJS."""
    args = ["--js-runtimes", "node"]
    if cookies_path and os.path.exists(cookies_path):
        args.extend(["--cookies", cookies_path])
    return args


def get_gdrive_service():
    """Initializes Google Drive API client using Refresh Token or OAuth credentials."""
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logger.warning("Google Drive credentials not fully set in environment.")
        return None

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    if not creds.valid:
        creds.refresh(Request())

    return build("drive", "v3", credentials=creds)


def parse_video_id_and_quality(filename: str) -> Tuple[Optional[str], int]:
    """Extracts video ID and resolution height from filenames."""
    video_id = None
    quality_height = 0

    id_matches = re.findall(r"\[([a-zA-Z0-9_-]{11})\]", filename)
    if id_matches:
        video_id = id_matches[-1]

    quality_matches = re.findall(r"(\d{3,4})p", filename, re.IGNORECASE)
    if quality_matches:
        try:
            quality_height = int(quality_matches[-1])
        except ValueError:
            quality_height = 0

    return video_id, quality_height


def scan_drive_folder(service, folder_id: str) -> Dict[str, Dict[str, Any]]:
    """Scans Google Drive folder to detect existing video resolutions."""
    if not service or not folder_id:
        return {}

    logger.info(f"Scanning existing files in Google Drive folder: {folder_id}...")
    existing = {}
    page_token = None

    while True:
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            res = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, size, createdTime)",
                pageSize=100,
                pageToken=page_token
            ).execute()

            for item in res.get("files", []):
                name = item.get("name", "")
                vid_id, height = parse_video_id_and_quality(name)
                if vid_id:
                    existing[vid_id] = {
                        "file_id": item.get("id"),
                        "name": name,
                        "height": height,
                        "size": int(item.get("size") or 0)
                    }

            page_token = res.get("nextPageToken")
            if not page_token:
                break
        except Exception as e:
            logger.error(f"Error reading Drive folder contents: {e}")
            break

    logger.info(f"Found {len(existing)} existing videos in Google Drive folder.")
    return existing


def upload_to_drive(service, file_path: Path, folder_id: str, old_file_id: Optional[str] = None) -> Optional[str]:
    """Uploads file to Google Drive and purges the old lower-quality file if updating."""
    if not service:
        logger.info(f"[DRIVE-LOCAL-MODE] Skipping live upload (file saved locally at {file_path}).")
        return "local_saved"

    filename = file_path.name
    logger.info(f"Uploading '{filename}' ({file_path.stat().st_size / (1024*1024):.1f} MB) to Drive...")

    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    media = MediaFileUpload(str(file_path), resumable=True)

    try:
        req = service.files().create(body=file_metadata, media_body=media, fields="id, name")
        response = None
        while response is None:
            status, response = req.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")

        new_file_id = response.get("id")
        logger.info(f"Upload successful! Google Drive File ID: {new_file_id}")

        if old_file_id and old_file_id != new_file_id:
            try:
                service.files().delete(fileId=old_file_id).execute()
                logger.info(f"Purged obsolete lower-resolution file (ID: {old_file_id}) from Drive.")
            except Exception as del_err:
                logger.warning(f"Could not remove old file {old_file_id}: {del_err}")

        return new_file_id
    except Exception as e:
        logger.error(f"Failed to upload {filename} to Google Drive: {e}")
        return None


def verify_file_resolution(file_path: Path) -> int:
    """Verifies actual video stream height using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=height",
            "-of", "csv=p=0",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = res.stdout.strip()
        if output.isdigit():
            return int(output)
    except Exception as e:
        logger.debug(f"ffprobe check failed: {e}")
    return 0


def probe_best_format(video_url: str, cookies_path: Optional[str] = None) -> Tuple[Optional[str], int, str]:
    """Find the highest video height actually exposed by a client."""
    logger.info(f"Probing video stream formats for {video_url}...")

    best_height = 0
    best_client = None
    best_format_id = None

    for client in PLAYER_CLIENT_CANDIDATES:
        cmd = [
            "yt-dlp", "--dump-single-json", "--skip-download",
            "--no-playlist", "--no-warnings",
            "--extractor-args", f"youtube:player_client={client}",
        ]
        cmd.extend(yt_dlp_common_args(cookies_path))
        cmd.append(video_url)

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if res.returncode != 0:
                logger.warning(f"Probe client '{client}' failed: {res.stderr[-500:]}")
                continue

            info = json.loads(res.stdout)
            formats = info.get("formats", [])
            videos = [
                f for f in formats
                if f.get("vcodec") not in (None, "none")
                and int(f.get("height") or 0) > 0
            ]
            if not videos:
                continue

            # Prefer formats with a direct URL; these are genuinely downloadable.
            direct = [f for f in videos if f.get("url")]
            candidates = direct or videos
            best = max(
                candidates,
                key=lambda f: (
                    int(f.get("height") or 0),
                    int(f.get("width") or 0),
                    float(f.get("fps") or 0),
                    float(f.get("tbr") or f.get("vbr") or 0),
                ),
            )
            height = int(best.get("height") or 0)
            logger.info(
                f"Client '{client}': max video={height}p "
                f"format={best.get('format_id')} direct={'YES' if best.get('url') else 'NO'}"
            )

            if height > best_height:
                best_height = height
                best_client = client
                best_format_id = best.get("format_id")

        except Exception as err:
            logger.warning(f"Client '{client}' probe error: {err}")

    if not best_client:
        return None, 0, ""

    return best_format_id, best_height, best_client

def download_video(
    video_url: str,
    target_client: str,
    cookies_path: Optional[str] = None,
    max_resolution: int = 2160
) -> Optional[Tuple[Path, int]]:
    """Download the best available video+audio and verify the resulting resolution."""
    output_template = str(DOWNLOADS_DIR / "%(title).200B [%(id)s] [%(height)sp].%(ext)s")
    format_selector = (
        f"bestvideo[height<={max_resolution}]+bestaudio/"
        f"bestvideo+bestaudio/best[height<={max_resolution}]/best"
    )

    strategies = [
        target_client,
        "web",
        "mweb",
        "tv",
        "android",
        "ios",
    ]
    seen = set()

    for client in strategies:
        if not client or client in seen:
            continue
        seen.add(client)

        for item in DOWNLOADS_DIR.glob("*"):
            if item.is_file():
                try:
                    item.unlink()
                except Exception:
                    pass

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--merge-output-format", "mkv",
            "-f", format_selector,
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
            logger.warning(
                f"Client '{client}' failed (code {res.returncode}): "
                f"{(res.stderr or res.stdout)[-700:]}"
            )
            continue

        downloaded_files = [
            f for f in DOWNLOADS_DIR.glob("*.mkv")
            if f.is_file()
        ]
        if not downloaded_files:
            logger.warning(f"Client '{client}' reported success but produced no MKV file.")
            continue

        latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
        actual_height = verify_file_resolution(latest_file)

        if actual_height <= 0:
            logger.warning(f"Downloaded file '{latest_file.name}' has no readable video resolution.")
            continue

        logger.info(
            f"Successfully downloaded: {latest_file.name} "
            f"(verified {actual_height}p)"
        )
        return latest_file, actual_height

    logger.error(f"All download strategies exhausted for {video_url}.")
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
    """Processes video, auto-upgrades if higher resolution exists."""
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
            logger.info(f"Video {video_id} is already in Drive at max resolution ({existing_height}p >= {available_height}p). Skipping.")
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
    """Extract playlist entries; never silently turn an extraction error into success."""
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
        logger.error(
            f"Playlist extraction failed with exit code {res.returncode}: "
            f"{res.stderr[-1000:]}"
        )
        return []

    urls = [
        line.strip() for line in res.stdout.splitlines()
        if line.strip().startswith(("http://", "https://"))
    ]
    logger.info(f"Found {len(urls)} videos in playlist.")

    if not urls:
        logger.error("Playlist extraction returned zero videos. Stopping instead of reporting success.")

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
        logger.error("No videos were extracted. GitHub Actions will be marked FAILED.")
        if cookies_path and os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
            except Exception:
                pass
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
        logger.error("No video was successfully synchronized. GitHub Actions will be marked FAILED.")
        if cookies_path and os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
            except Exception:
                pass
        sys.exit(1)

    logger.info(f"Successfully synchronized {success_count}/{len(video_urls)} video(s).")

    if cookies_path and os.path.exists(cookies_path):
        try:
            os.remove(cookies_path)
        except Exception:
            pass

    logger.info("\nAll tasks completed successfully!")


if __name__ == "__main__":
    main()
