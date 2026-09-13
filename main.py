# ==============================================================================
# YouTube -> Google Drive
# دانلود بالاترین کیفیت واقعاً قابل دانلود برای هر ویدیو
# ==============================================================================

import mimetypes
import os
import logging
import subprocess

import yt_dlp

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


# ==============================================================================
# Logging
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DOWNLOAD_FOLDER = "downloads"
COOKIE_FILE = "cookies.txt"

# Probe all current player clients instead of assuming one fixed client.
PLAYER_CLIENT_CANDIDATES = [
    "web",
    "web_safari",
    "web_embedded",
    "web_music",
    "web_creator",
    "mweb",
    "ios",
    "visionos",
    "android",
    "android_vr",
    "tv",
    "tv_downgraded",
    "tv_simply",
]


# ==============================================================================
# Environment
# ==============================================================================

def setup_environment():
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    logging.info("Download folder ready: %s", DOWNLOAD_FOLDER)


# ==============================================================================
# Google Drive
# ==============================================================================

def get_gdrive_service():
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logging.error("Google Drive credentials are missing.")
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )
        creds.refresh(Request())

        service = build("drive", "v3", credentials=creds)
        logging.info("Google Drive connection successful.")
        return service
    except Exception as exc:
        logging.error("Google Drive connection error: %s", exc)
        return None


def list_video_files_in_gdrive(service, folder_id, video_id):
    """Return files in the target folder whose name contains this video id."""
    try:
        query = (
            f"'{folder_id}' in parents "
            f"and name contains '{video_id}' "
            f"and trashed=false"
        )
        result = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id,name)",
            pageSize=100,
        ).execute()
        return result.get("files", [])
    except Exception as exc:
        logging.error("Google Drive search error: %s", exc)
        return []


def is_quality_tagged_name(name, video_id):
    """Recognize files created by this version, e.g. '[abc123] [1080p]'."""
    marker = f"[{video_id}] ["
    return marker in name and name.endswith("]") is False


def upload_to_gdrive(service, folder_id, file_path):
    try:
        filename = os.path.basename(file_path)
        logging.info("Uploading to Google Drive: %s", filename)

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True,
        )

        result = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name",
        ).execute()

        logging.info("Upload successful. File ID: %s", result.get("id"))
        return result.get("id")
    except Exception as exc:
        logging.error("Upload error: %s", exc)
        return None


def delete_drive_file(service, file_id, filename):
    try:
        service.files().delete(fileId=file_id).execute()
        logging.info("Removed old Drive file: %s", filename)
        return True
    except Exception as exc:
        logging.warning("Could not remove old Drive file %s: %s", filename, exc)
        return False


# ==============================================================================
# YouTube helpers
# ==============================================================================

def build_youtube_opts(cookie_path, player_client):
    opts = {
        "js_runtimes": {"node": {}},
        "extractor_args": {
            "youtube": [f"player_client={player_client}"],
        },
    }
    if cookie_path:
        opts["cookiefile"] = cookie_path
    return opts


def quality_score(fmt):
    return (
        int(fmt.get("height") or 0),
        int(fmt.get("width") or 0),
        float(fmt.get("fps") or 0),
        float(fmt.get("tbr") or 0),
    )


def format_label(fmt):
    if not fmt:
        return "NONE"
    height = int(fmt.get("height") or 0)
    width = int(fmt.get("width") or 0)
    resolution = fmt.get("resolution") or f"{width}x{height}"
    return (
        f"format={fmt.get('format_id')} "
        f"resolution={resolution} "
        f"fps={fmt.get('fps')} "
        f"tbr={fmt.get('tbr')}"
    )


def collect_downloadable_candidates(info, player_client):
    """Collect real video/audio URLs only; formats without URL are never selected."""
    formats = info.get("formats") or []

    videos = [
        f for f in formats
        if f.get("url")
        and f.get("vcodec") not in (None, "none")
        and int(f.get("height") or 0) > 0
    ]

    audios = [
        f for f in formats
        if f.get("url")
        and f.get("acodec") not in (None, "none")
        and f.get("vcodec") in (None, "none")
    ]

    if not videos:
        return []

    best_audio = None
    if audios:
        best_audio = max(
            audios,
            key=lambda f: (
                float(f.get("abr") or 0),
                float(f.get("tbr") or 0),
            ),
        )

    candidates = []
    for video in videos:
        candidates.append(
            {
                "client": player_client,
                "video": video,
                "audio": best_audio,
                "score": quality_score(video),
            }
        )

    return candidates


def probe_best_downloadable_formats(video_url, cookie_path):
    """Probe every client and return all directly downloadable candidates, best first."""
    candidates = []

    for client in PLAYER_CLIENT_CANDIDATES:
        logging.info("Probing YouTube client: %s", client)
        opts = build_youtube_opts(cookie_path, client)
        opts.update({
            "quiet": True,
            "no_warnings": False,
            "ignoreerrors": True,
            "skip_download": True,
        })

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

            if not info:
                logging.warning("%s: no video information returned", client)
                continue

            client_candidates = collect_downloadable_candidates(info, client)
            if not client_candidates:
                logging.warning(
                    "%s: no directly downloadable video format found", client
                )
                continue

            best = max(client_candidates, key=lambda item: item["score"])
            logging.info(
                "%s: highest directly downloadable = %s",
                client,
                format_label(best["video"]),
            )
            candidates.extend(client_candidates)

        except Exception as exc:
            logging.warning("%s probe failed: %s", client, exc)

    candidates.sort(key=lambda item: item["score"], reverse=True)

    # De-duplicate identical client/format combinations.
    unique = []
    seen = set()
    for candidate in candidates:
        key = (candidate["client"], candidate["video"].get("format_id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)

    return unique


def build_format_selector(candidate):
    video_id = candidate["video"].get("format_id")
    audio_id = candidate["audio"].get("format_id") if candidate["audio"] else None

    if audio_id:
        return f"{video_id}+{audio_id}"
    return video_id


def verify_downloaded_height(file_path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                file_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        line = result.stdout.strip()
        width, height = line.split(",")
        return int(width), int(height)
    except Exception as exc:
        logging.warning("Could not verify downloaded resolution: %s", exc)
        return 0, 0


def download_best_quality(video_url, cookie_path, video_id, title):
    """Try candidates from highest to lowest until a real successful download is verified."""
    candidates = probe_best_downloadable_formats(video_url, cookie_path)

    if not candidates:
        logging.error(
            "No directly downloadable video format was found for %s. "
            "No 360p fallback will be used as a fake maximum.",
            video_id,
        )
        return None

    best = candidates[0]
    logging.info(
        "MAX DIRECTLY DOWNLOADABLE QUALITY DETECTED: %s via client=%s",
        format_label(best["video"]),
        best["client"],
    )

    tried = set()

    for index, candidate in enumerate(candidates, start=1):
        client = candidate["client"]
        selected_video = candidate["video"]
        selected_height = int(selected_video.get("height") or 0)
        selected_width = int(selected_video.get("width") or 0)
        selector = build_format_selector(candidate)
        key = (client, selector)

        if key in tried:
            continue
        tried.add(key)

        logging.info(
            "Download attempt %d/%d: client=%s quality=%sp format=%s",
            index,
            len(candidates),
            client,
            selected_height,
            selector,
        )

        output_template = (
            f"{DOWNLOAD_FOLDER}/%(title)s [{video_id}] "
            f"[{selected_height}p].%(ext)s"
        )

        download_opts = {
            "format": selector,
            "outtmpl": output_template,
            "merge_output_format": "mkv",
            "js_runtimes": {"node": {}},
            "extractor_args": {
                "youtube": [f"player_client={client}"],
            },
            "retries": 3,
            "fragment_retries": 3,
            "concurrent_fragment_downloads": 4,
            "sleep_interval": 2,
            "max_sleep_interval": 5,
            "quiet": False,
            "verbose": True,
        }

        if cookie_path:
            download_opts["cookiefile"] = cookie_path

        try:
            with yt_dlp.YoutubeDL(download_opts) as dl:
                info = dl.extract_info(video_url, download=True)
                if not info:
                    raise RuntimeError("yt-dlp returned no video information")

                file_path = dl.prepare_filename(info)

            if not os.path.exists(file_path):
                base = os.path.splitext(file_path)[0]
                for ext in ("mkv", "mp4", "webm", "mp4"):
                    candidate_path = f"{base}.{ext}"
                    if os.path.exists(candidate_path):
                        file_path = candidate_path
                        break

            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)

            actual_width, actual_height = verify_downloaded_height(file_path)
            logging.info(
                "Downloaded file verified: %sx%s; requested=%sx%s",
                actual_width,
                actual_height,
                selected_width,
                selected_height,
            )

            if actual_height < selected_height:
                raise RuntimeError(
                    f"Downloaded resolution {actual_width}x{actual_height} is below "
                    f"requested {selected_width}x{selected_height}"
                )

            logging.info(
                "SUCCESS: highest working candidate is %sp (%s)",
                actual_height,
                selector,
            )
            return {
                "file_path": file_path,
                "height": actual_height,
                "width": actual_width,
                "client": client,
                "selector": selector,
                "title": title,
            }

        except Exception as exc:
            logging.warning(
                "Download candidate failed (%s, %s): %s",
                client,
                selector,
                exc,
            )

    logging.error("All tested downloadable quality candidates failed for %s", video_id)
    return None


# ==============================================================================
# Playlist processing
# ==============================================================================

def process_playlist():
    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    if not playlist_url:
        logging.error("YOUTUBE_PLAYLIST_URL is missing.")
        return
    if not folder_id:
        logging.error("GDRIVE_FOLDER_ID is missing.")
        return

    service = get_gdrive_service()
    if not service:
        return

    cookie_path = COOKIE_FILE if os.path.exists(COOKIE_FILE) else None
    logging.info("YouTube cookies: %s", "available" if cookie_path else "not found")

    playlist_opts = {
        "extract_flat": "in_playlist",
        "quiet": False,
        "js_runtimes": {"node": {}},
    }
    if cookie_path:
        playlist_opts["cookiefile"] = cookie_path

    try:
        with yt_dlp.YoutubeDL(playlist_opts) as ydl:
            logging.info("Reading playlist...")
            playlist_info = ydl.extract_info(playlist_url, download=False)
    except Exception as exc:
        logging.error("Playlist extraction failed: %s", exc)
        return

    if not playlist_info or "entries" not in playlist_info:
        logging.error("No videos were found in playlist.")
        return

    for video in playlist_info["entries"]:
        if not video:
            continue

        video_id = video.get("id")
        if not video_id:
            continue

        video_url = video.get("webpage_url") or video.get("url")
        if not video_url or "watch?v=" not in video_url:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        title = video.get("title") or video_id

        logging.info("=" * 100)
        logging.info("Starting video: %s", video_id)
        logging.info("Title: %s", title)

        existing_files = list_video_files_in_gdrive(service, folder_id, video_id)
        quality_tagged = [
            item for item in existing_files
            if f"[{video_id}] [" in item.get("name", "")
        ]

        if quality_tagged:
            logging.info(
                "Already downloaded by this quality-aware version: %s",
                ", ".join(item.get("name", "") for item in quality_tagged),
            )
            continue

        if existing_files:
            logging.info(
                "Legacy file(s) found for %s; they will be replaced by the "
                "highest actually downloadable quality.",
                video_id,
            )

        result = download_best_quality(video_url, cookie_path, video_id, title)
        if not result:
            continue

        file_path = result["file_path"]
        logging.info(
            "FINAL QUALITY: %sx%s | client=%s | format=%s",
            result["width"],
            result["height"],
            result["client"],
            result["selector"],
        )

        uploaded_id = upload_to_gdrive(service, folder_id, file_path)
        if not uploaded_id:
            continue

        # Delete legacy copies so the old 360p version cannot remain alongside
        # the newly selected maximum-quality file.
        for old in existing_files:
            old_id = old.get("id")
            old_name = old.get("name", "")
            if old_id and old_id != uploaded_id:
                delete_drive_file(service, old_id, old_name)

        try:
            os.remove(file_path)
            logging.info("Local file deleted after successful upload.")
        except Exception as exc:
            logging.warning("Could not delete local file: %s", exc)


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    setup_environment()
    process_playlist()
