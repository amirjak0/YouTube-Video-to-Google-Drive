# ==============================================================================
# YouTube -> Google Drive
# دانلود بالاترین کیفیت موجود با انتخاب خودکار بهترین YouTube client
# ==============================================================================

import os
import logging
import mimetypes
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)


DOWNLOAD_FOLDER = 'downloads'
COOKIE_FILE = 'cookies.txt'

# Try the normal/default client set first, then explicit fallbacks.
# `default` is intentionally first because yt-dlp adapts its YouTube clients
# to the current authentication/runtime situation.
PLAYER_CLIENT_CANDIDATES = [
    'default',
    'web_creator',
    'web_safari',
    'web_embedded',
    'mweb',
]


# ==============================================================================
# Environment
# ==============================================================================

def setup_environment():
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    logging.info(f"Download folder ready: {DOWNLOAD_FOLDER}")


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
            client_secret=client_secret
        )

        creds.refresh(Request())

        service = build(
            "drive",
            "v3",
            credentials=creds
        )

        logging.info("Google Drive connection successful.")
        return service

    except Exception as e:
        logging.error(f"Google Drive connection error: {e}")
        return None


# ==============================================================================
# Check if video already exists
# ==============================================================================

def video_exists_in_gdrive(service, folder_id, video_id):
    try:
        query = (
            f"'{folder_id}' in parents "
            f"and name contains '{video_id}' "
            f"and trashed=false"
        )

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id,name)'
        ).execute()

        return len(results.get("files", [])) > 0

    except Exception as e:
        logging.error(f"Google Drive search error: {e}")
        return False


# ==============================================================================
# Upload
# ==============================================================================

def upload_to_gdrive(service, folder_id, file_path):
    try:
        filename = os.path.basename(file_path)

        logging.info(f"Uploading to Google Drive: {filename}")

        file_metadata = {
            "name": filename,
            "parents": [folder_id]
        }

        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type is None:
            mime_type = "application/octet-stream"

        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True
        )

        result = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        logging.info(f"Upload successful. File ID: {result.get('id')}")
        return True

    except Exception as e:
        logging.error(f"Upload error: {e}")
        return False


# ==============================================================================
# YouTube options
# ==============================================================================

def build_youtube_opts(cookie_path, player_client):
    return {
        "cookiefile": cookie_path,
        "js_runtimes": {
            "node": {}
        },
        "extractor_args": {
            "youtube": [
                f"player_client={player_client}"
            ]
        },
    }


def get_video_quality_score(fmt):
    """Return a sortable quality score for a video format."""
    return (
        int(fmt.get("height") or 0),
        int(fmt.get("width") or 0),
        float(fmt.get("fps") or 0),
        float(fmt.get("tbr") or 0),
    )


def get_best_available_format_info(info):
    """
    Find the best video-capable format exposed by yt-dlp.
    Separate video-only formats are considered because the final download can
    merge the best video and best audio streams.
    """
    formats = info.get("formats") or []
    video_formats = [
        f for f in formats
        if f.get("vcodec") not in (None, "none")
        and (f.get("height") or 0) > 0
    ]

    if not video_formats:
        return None

    return max(video_formats, key=get_video_quality_score)


def choose_best_player_client(video_url, cookie_path):
    """
    Probe each candidate client automatically and select the client exposing
    the highest-quality usable video formats. This avoids hard-coding mweb.
    """
    best_result = None
    best_score = (-1, -1, -1, -1)

    for player_client in PLAYER_CLIENT_CANDIDATES:
        logging.info(f"Probing YouTube client: {player_client}")

        probe_opts = build_youtube_opts(cookie_path, player_client)
        probe_opts.update({
            "quiet": True,
            "no_warnings": False,
            "ignoreerrors": True,
        })

        try:
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

            if not info:
                logging.warning(f"Client {player_client}: no video info returned.")
                continue

            best_format = get_best_available_format_info(info)

            if not best_format:
                logging.warning(
                    f"Client {player_client}: no usable video format found."
                )
                continue

            score = get_video_quality_score(best_format)
            logging.info(
                "Client %s: best video = format %s, resolution=%s, fps=%s, tbr=%s",
                player_client,
                best_format.get("format_id"),
                best_format.get("resolution"),
                best_format.get("fps"),
                best_format.get("tbr"),
            )

            if score > best_score:
                best_score = score
                best_result = {
                    "player_client": player_client,
                    "info": info,
                    "best_format": best_format,
                    "score": score,
                }

        except Exception as e:
            logging.warning(
                f"Client {player_client} probe failed: {e}"
            )

    if best_result:
        bf = best_result["best_format"]
        logging.info(
            "Selected YouTube client automatically: %s",
            best_result["player_client"],
        )
        logging.info(
            "Best detected video quality: %s (format %s)",
            bf.get("resolution"),
            bf.get("format_id"),
        )
        return best_result["player_client"]

    logging.warning(
        "No candidate client produced a usable video format. Falling back to default client set."
    )
    return "default"


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

    if cookie_path:
        logging.info("YouTube cookies detected.")
    else:
        logging.warning("cookies.txt was not found.")

    # For the playlist itself, do NOT force mweb. Let yt-dlp use its current
    # playlist extraction behavior; the per-video client is chosen below.
    playlist_opts = {
        "extract_flat": "in_playlist",
        "quiet": False,
        "cookiefile": cookie_path,
        "js_runtimes": {
            "node": {}
        },
    }

    try:
        with yt_dlp.YoutubeDL(playlist_opts) as ydl:
            logging.info("Reading playlist...")
            playlist_info = ydl.extract_info(
                playlist_url,
                download=False
            )
    except Exception as e:
        logging.error(f"Playlist extraction failed: {e}")
        return

    if not playlist_info:
        logging.error("Playlist information could not be retrieved.")
        return

    if "entries" not in playlist_info:
        logging.error("No videos were found in playlist.")
        return

    for video in playlist_info["entries"]:
        if not video:
            continue

        video_id = video.get("id")
        if not video_id:
            continue

        if video_exists_in_gdrive(service, folder_id, video_id):
            logging.info(f"Already exists in Google Drive: {video_id}")
            continue

        logging.info("=" * 80)
        logging.info(f"Starting download: {video_id}")
        logging.info("Automatically selecting the highest available quality...")

        video_url = video.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        selected_client = choose_best_player_client(video_url, cookie_path)

        download_opts = {
            "format": "bestvideo*+bestaudio/best",
            "outtmpl": (
                f"{DOWNLOAD_FOLDER}/"
                "%(title)s "
                f"[{video_id}].%(ext)s"
            ),
            "merge_output_format": "mkv",
            "cookiefile": cookie_path,
            "js_runtimes": {
                "node": {}
            },
            "extractor_args": {
                "youtube": [
                    f"player_client={selected_client}"
                ]
            },
            "format_sort": [
                "res",
                "fps",
                "br",
                "vcodec:av01",
                "acodec"
            ],
            "ignoreerrors": True,
            "sleep_interval": 5,
            "max_sleep_interval": 15,
            "verbose": True,
        }

        try:
            with yt_dlp.YoutubeDL(download_opts) as dl:
                info = dl.extract_info(
                    video_url,
                    download=True
                )

                if info is None:
                    logging.warning(
                        f"Download failed or video unavailable: {video_id}"
                    )
                    continue

                requested_formats = info.get("requested_formats")

                if requested_formats:
                    logging.info("Selected separate video/audio streams:")
                    for fmt in requested_formats:
                        logging.info(
                            "  format_id=%s resolution=%s fps=%s vcodec=%s acodec=%s tbr=%s",
                            fmt.get("format_id"),
                            fmt.get("resolution"),
                            fmt.get("fps"),
                            fmt.get("vcodec"),
                            fmt.get("acodec"),
                            fmt.get("tbr"),
                        )
                else:
                    logging.info(
                        f"Selected single format: {info.get('format_id')}"
                    )

                file_path = dl.prepare_filename(info)

                if not os.path.exists(file_path):
                    base_path = os.path.splitext(file_path)[0]
                    possible_paths = [
                        base_path + ".mkv",
                        base_path + ".mp4",
                        base_path + ".webm"
                    ]

                    found = False
                    for candidate in possible_paths:
                        if os.path.exists(candidate):
                            file_path = candidate
                            found = True
                            break

                    if not found:
                        logging.error(
                            f"Downloaded file was not found: {file_path}"
                        )
                        continue

                logging.info(f"Downloaded file: {file_path}")

                upload_ok = upload_to_gdrive(
                    service,
                    folder_id,
                    file_path
                )

                if upload_ok:
                    try:
                        os.remove(file_path)
                        logging.info(
                            "Local file deleted after successful upload."
                        )
                    except Exception as e:
                        logging.warning(
                            f"Could not delete local file: {e}"
                        )

        except Exception as e:
            logging.error(f"Error processing {video_id}: {e}")


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    setup_environment()
    process_playlist()
