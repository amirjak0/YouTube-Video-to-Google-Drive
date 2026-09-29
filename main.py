#!/usr/bin/env python3
"""
YouTube Video to Google Drive - High Quality Auto-Updater & Synchronizer

Quality fixes:
- Probes multiple YouTube player clients and records the best available video format.
- Downloads using the selected client instead of discarding the probe result.
- Selects best video + best audio, up to the configured resolution.
- Verifies the actual downloaded height with ffprobe.
- Never uploads a file below the requested minimum quality.
- Retries with other clients when a client only exposes a low-resolution stream.
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

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("yt-gdrive-sync")
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

PLAYER_CLIENT_CANDIDATES = ["web", "tv", "web_safari", "ios", "android", "tv_simply", "mweb"]


def get_gdrive_service():
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
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    if not creds.valid:
        creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def parse_video_id_and_quality(filename: str) -> Tuple[Optional[str], int]:
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
    if not service or not folder_id:
        return {}
    logger.info(f"Scanning existing files in Google Drive folder: {folder_id}...")
    existing, page_token = {}, None
    while True:
        try:
            query = f"'{folder_id}' in parents and trashed = false"
            res = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, size, createdTime)",
                pageSize=100,
                pageToken=page_token,
            ).execute()
            for item in res.get("files", []):
                name = item.get("name", "")
                vid_id, height = parse_video_id_and_quality(name)
                if vid_id:
                    existing[vid_id] = {
                        "file_id": item.get("id"),
                        "name": name,
                        "height": height,
                        "size": int(item.get("size") or 0),
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
    if not service:
        logger.info(f"[DRIVE-LOCAL-MODE] Skipping live upload (file saved locally at {file_path}).")
        return "local_saved"
    filename = file_path.name
    logger.info(f"Uploading '{filename}' ({file_path.stat().st_size / (1024 * 1024):.1f} MB) to Drive...")
    file_metadata = {"name": filename, "parents": [folder_id]}
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
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=height", "-of", "csv=p=0", str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = res.stdout.strip()
        if output.isdigit():
            return int(output)
    except Exception as e:
        logger.debug(f"ffprobe check failed: {e}")
    return 0


def cleanup_downloads():
    for item in DOWNLOADS_DIR.iterdir():
        if item.is_file():
            try:
                item.unlink()
            except Exception:
                pass


def probe_best_format(video_url: str, cookies_path: Optional[str] = None) -> Tuple[Optional[str], int, str]:
    """Return (format_id, height, client) for the highest video-only stream found."""
    logger.info(f"Probing video stream formats for {video_url}...")
    best_height = 0
    best_client = None
    best_format_id = None

    for client in PLAYER_CLIENT_CANDIDATES:
        cmd = [
            "yt-dlp", "--dump-single-json", "--no-playlist",
            "--js-runtimes", "node",
            "--extractor-args", f"youtube:player_client={client}",
        ]
        if cookies_path and os.path.exists(cookies_path):
            cmd.extend(["--cookies", cookies_path])
        cmd.append(video_url)

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            if res.returncode != 0:
                continue
            info = json.loads(res.stdout)
            formats = info.get("formats", [])

            candidates = []
            for f in formats:
                height = int(f.get("height") or 0)
                vcodec = f.get("vcodec")
                if vcodec in (None, "none") or height <= 0:
                    continue
                candidates.append(f)

            if not candidates:
                continue

            candidates.sort(
                key=lambda x: (
                    int(x.get("height") or 0),
                    int(x.get("width") or 0),
                    float(x.get("fps") or 0),
                    float(x.get("vbr") or x.get("tbr") or 0),
                ),
                reverse=True,
            )
            top = candidates[0]
            client_height = int(top.get("height") or 0)
            logger.info(
                f"Client '{client}' max video: {client_height}p "
                f"(format_id: {top.get('format_id')})"
            )

            if client_height > best_height:
                best_height = client_height
                best_client = client
                best_format_id = str(top.get("format_id"))
        except Exception as err:
            logger.debug(f"Client {client} probe error: {err}")

    if not best_format_id:
        return None, 0, ""

    return best_format_id, best_height, best_client


def download_video(
    video_url: str,
    target_client: str,
    cookies_path: Optional[str] = None,
    max_resolution: int = 2160,
    preferred_format: Optional[str] = None,
    expected_height: int = 0,
) -> Optional[Tuple[Path, int]]:
    """Download high-quality video and reject low-resolution results."""
    output_template = str(DOWNLOADS_DIR / "%(title).200B [%(id)s] [%(height)sp].%(ext)s")

    # Try the exact probed format first. Then try bestvideo+bestaudio through
    # the same client. Finally use other clients as fallbacks.
    clients = []
    if target_client:
        clients.append(target_client)
    for client in PLAYER_CLIENT_CANDIDATES:
        if client not in clients:
            clients.append(client)

    min_acceptable = expected_height if expected_height > 0 else 720
    min_acceptable = min(min_acceptable, max_resolution)

    for client in clients:
        strategies = []
        if preferred_format:
            strategies.append((
                f"{preferred_format}+bestaudio/{preferred_format}",
                f"exact probed format {preferred_format}"
            ))
        strategies.append((
            f"bestvideo[height<={max_resolution}]+bestaudio/best[height<={max_resolution}]",
            f"best available <= {max_resolution}p"
        ))

        for format_selector, format_desc in strategies:
            cleanup_downloads()
            cmd = [
                "yt-dlp", "--no-playlist",
                "--merge-output-format", "mkv",
                "-f", format_selector,
                "--js-runtimes", "node",
                "--extractor-args", f"youtube:player_client={client}",
                "-o", output_template,
                "--embed-metadata",
                "--no-mtime",
                "--no-overwrites",
            ]
            if cookies_path and os.path.exists(cookies_path):
                cmd.extend(["--cookies", cookies_path])
            cmd.append(video_url)

            logger.info(f"Attempting {format_desc} via client '{client}'...")
            res = subprocess.run(cmd, capture_output=True, text=True)

            if "The page needs to be reloaded" in (res.stderr or ""):
                logger.warning(f"Client '{client}' triggered YouTube reload check. Trying another client...")
                continue
            if res.returncode != 0:
                logger.warning(
                    f"Download failed via '{client}' ({res.returncode}): "
                    f"{(res.stderr or '')[-500:]}"
                )
                continue

            downloaded_files = list(DOWNLOADS_DIR.glob("*.mkv")) or list(DOWNLOADS_DIR.glob("*.*"))
            if not downloaded_files:
                continue

            latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
            actual_height = verify_file_resolution(latest_file)
            logger.info(
                f"Downloaded: {latest_file.name} | verified resolution: {actual_height}p"
            )

            if actual_height < min_acceptable:
                logger.warning(
                    f"REJECTED: downloaded file is only {actual_height}p; "
                    f"minimum acceptable is {min_acceptable}p. Trying another strategy/client."
                )
                cleanup_downloads()
                continue

            return latest_file, actual_height

    logger.error(
        f"All high-quality download strategies exhausted for {video_url}. "
        f"No file meeting {min_acceptable}p was accepted."
    )
    return None


def process_single_video(
    video_url: str,
    gdrive_service,
    folder_id: str,
    existing_drive_files: Dict[str, Dict[str, Any]],
    update_existing: bool = True,
    cookies_path: Optional[str] = None,
    force_quality_limit: int = 2160,
):
    logger.info(f"\n=======================================================\nProcessing video: {video_url}")
    id_match = re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", video_url)
    video_id = id_match.group(1) if id_match else None

    best_format_id, available_height, chosen_client = probe_best_format(video_url, cookies_path)
    if not best_format_id or available_height <= 0:
        logger.error("Could not find a usable video stream from any player client.")
        return

    requested_max = min(force_quality_limit, available_height)
    logger.info(
        f"Highest downloadable resolution found: {available_height}p "
        f"via {chosen_client}; download limit: {requested_max}p; format: {best_format_id}"
    )

    existing_entry = existing_drive_files.get(video_id) if video_id else None
    old_file_id = None
    if existing_entry:
        existing_height = existing_entry.get("height", 0)
        old_file_id = existing_entry.get("file_id")
        old_name = existing_entry.get("name")
        logger.info(f"Found existing Drive file: '{old_name}' ({existing_height}p)")

        if existing_height >= available_height and not os.environ.get("FORCE_RETRY"):
            logger.info(
                f"Video {video_id} is already at max detected resolution "
                f"({existing_height}p >= {available_height}p). Skipping."
            )
            return

        if not update_existing and not os.environ.get("FORCE_RETRY"):
            logger.info(f"Update existing is disabled. Skipping {video_id}.")
            return

    download_res = download_video(
        video_url,
        target_client=chosen_client,
        cookies_path=cookies_path,
        max_resolution=requested_max,
        preferred_format=best_format_id,
        expected_height=available_height,
    )
    if not download_res:
        logger.error(f"Failed to obtain an acceptable high-resolution stream for {video_url}.")
        return

    downloaded_file, verified_height = download_res

    # Never upload an unexpectedly low-quality file.
    if verified_height < available_height:
        logger.warning(
            f"Final verification failed: expected up to {available_height}p, "
            f"got {verified_height}p. File will NOT be uploaded."
        )
        try:
            downloaded_file.unlink()
        except Exception:
            pass
        return

    uploaded_id = upload_to_drive(
        gdrive_service,
        downloaded_file,
        folder_id,
        old_file_id=old_file_id,
    )
    if uploaded_id:
        logger.info(f"SUCCESS: Video {video_id or ''} synced to Google Drive at {verified_height}p!")
        try:
            downloaded_file.unlink()
        except Exception:
            pass


def get_playlist_videos(playlist_url: str) -> List[str]:
    if "list=" not in playlist_url:
        return [playlist_url]
    logger.info(f"Extracting video list from playlist: {playlist_url}...")
    cmd = ["yt-dlp", "--flat-playlist", "--print", "url", playlist_url]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        urls = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        logger.info(f"Found {len(urls)} videos in playlist.")
        return urls
    except Exception as e:
        logger.error(f"Failed to extract playlist entries: {e}")
        return [playlist_url]


def main():
    print("================================================================")
    print("YouTube Video to Google Drive - High Quality Auto-Updater & Sync")
    print("================================================================")

    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL") or os.environ.get("YOUTUBE_VIDEO_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID", "")
    update_existing = os.environ.get("UPDATE_EXISTING", "true").lower() in ("true", "1", "yes")
    force_quality_limit = int(os.environ.get("FORCE_QUALITY_LIMIT", "2160"))
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
    video_urls = get_playlist_videos(playlist_url)

    for idx, video_url in enumerate(video_urls, 1):
        logger.info(f"\nProcessing [{idx}/{len(video_urls)}]: {video_url}")
        try:
            process_single_video(
                video_url,
                service,
                folder_id,
                existing_drive_files,
                update_existing,
                cookies_path,
                force_quality_limit=force_quality_limit,
            )
        except Exception as err:
            logger.error(f"An unexpected error occurred for {video_url}: {err}")

    if cookies_path and os.path.exists(cookies_path):
        try:
            os.remove(cookies_path)
        except Exception:
            pass

    logger.info("\nAll tasks completed successfully!")


if __name__ == "__main__":
    main()
