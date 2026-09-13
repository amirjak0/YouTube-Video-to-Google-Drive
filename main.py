# ==============================================================================
# YouTube -> Google Drive
# دانلود بالاترین کیفیت موجود با yt-dlp + PO Token Provider
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
        logging.error(
            f"Google Drive search error: {e}"
        )
        return False


# ==============================================================================
# Upload
# ==============================================================================

def upload_to_gdrive(service, folder_id, file_path):
    try:
        filename = os.path.basename(file_path)

        logging.info(
            f"Uploading to Google Drive: {filename}"
        )

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

        logging.info(
            f"Upload successful. File ID: {result.get('id')}"
        )

        return True

    except Exception as e:
        logging.error(
            f"Upload error: {e}"
        )
        return False


# ==============================================================================
# Playlist processing
# ==============================================================================

def process_playlist():

    playlist_url = os.environ.get(
        "YOUTUBE_PLAYLIST_URL"
    )

    folder_id = os.environ.get(
        "GDRIVE_FOLDER_ID"
    )

    if not playlist_url:
        logging.error(
            "YOUTUBE_PLAYLIST_URL is missing."
        )
        return

    if not folder_id:
        logging.error(
            "GDRIVE_FOLDER_ID is missing."
        )
        return

    # --------------------------------------------------------------------------
    # Google Drive
    # --------------------------------------------------------------------------

    service = get_gdrive_service()

    if not service:
        return

    # --------------------------------------------------------------------------
    # Cookies
    # --------------------------------------------------------------------------

    cookie_path = (
        COOKIE_FILE
        if os.path.exists(COOKIE_FILE)
        else None
    )

    if cookie_path:
        logging.info("YouTube cookies detected.")
    else:
        logging.warning(
            "cookies.txt was not found."
        )

    # ==============================================================================
    # Playlist extractor options
    # ==============================================================================

    playlist_opts = {

        "extract_flat": "in_playlist",

        "quiet": False,

        "cookiefile": cookie_path,

        # Node.js for JS challenges
        "js_runtimes": {
            "node": {}
        },

        # IMPORTANT:
        # mweb is used because the current yt-dlp PO Token guide
        # recommends mweb + PO Token Provider for GVS requests.
        "extractor_args": {
            "youtube": [
                "player_client=mweb"
            ]
        }
    }

    # ==============================================================================
    # Read playlist
    # ==============================================================================

    try:

        with yt_dlp.YoutubeDL(playlist_opts) as ydl:

            logging.info(
                "Reading playlist..."
            )

            playlist_info = ydl.extract_info(
                playlist_url,
                download=False
            )

    except Exception as e:

        logging.error(
            f"Playlist extraction failed: {e}"
        )

        return

    if not playlist_info:
        logging.error(
            "Playlist information could not be retrieved."
        )
        return

    if "entries" not in playlist_info:
        logging.error(
            "No videos were found in playlist."
        )
        return

    # ==============================================================================
    # Process videos
    # ==============================================================================

    for video in playlist_info["entries"]:

        if not video:
            continue

        video_id = video.get("id")

        if not video_id:
            continue

        # --------------------------------------------------------------------------
        # Already exists?
        # --------------------------------------------------------------------------

        if video_exists_in_gdrive(
            service,
            folder_id,
            video_id
        ):

            logging.info(
                f"Already exists in Google Drive: {video_id}"
            )

            continue

        logging.info(
            "=" * 80
        )

        logging.info(
            f"Starting download: {video_id}"
        )

        logging.info(
            "Selecting the highest available video + audio quality..."
        )

        # ==============================================================================
        # Download options
        # ==============================================================================

        download_opts = {

            # ----------------------------------------------------------------------
            # HIGHEST AVAILABLE QUALITY
            #
            # Prefer separate best video + best audio.
            # If separate streams are unavailable, fallback to best single file.
            # ----------------------------------------------------------------------

            "format": (
                "bestvideo*+bestaudio/"
                "best"
            ),

            # ----------------------------------------------------------------------
            # Output file
            # ----------------------------------------------------------------------

            "outtmpl": (
                f"{DOWNLOAD_FOLDER}/"
                "%(title)s "
                f"[{video_id}].%(ext)s"
            ),

            # ----------------------------------------------------------------------
            # Final container
            # ----------------------------------------------------------------------

            "merge_output_format": "mkv",

            # ----------------------------------------------------------------------
            # Cookies
            # ----------------------------------------------------------------------

            "cookiefile": cookie_path,

            # ----------------------------------------------------------------------
            # JavaScript
            # ----------------------------------------------------------------------

            "js_runtimes": {
                "node": {}
            },

            # ----------------------------------------------------------------------
            # IMPORTANT:
            # Use mweb so the installed PO Token Provider can generate the
            # required token automatically.
            # ----------------------------------------------------------------------

            "extractor_args": {
                "youtube": [
                    "player_client=mweb"
                ]
            },

            # ----------------------------------------------------------------------
            # Sorting:
            # highest resolution first
            # highest fps first
            # highest bitrate first
            # ----------------------------------------------------------------------

            "format_sort": [
                "res",
                "fps",
                "br",
                "vcodec:av01",
                "acodec"
            ],

            # ----------------------------------------------------------------------
            # Keep going if one video fails
            # ----------------------------------------------------------------------

            "ignoreerrors": True,

            # ----------------------------------------------------------------------
            # Small delay between videos
            # ----------------------------------------------------------------------

            "sleep_interval": 5,

            "max_sleep_interval": 15,

            # ----------------------------------------------------------------------
            # Log format selection clearly
            # ----------------------------------------------------------------------

            "verbose": True
        }

        # ==============================================================================
        # Download
        # ==============================================================================

        try:

            with yt_dlp.YoutubeDL(download_opts) as dl:

                info = dl.extract_info(
                    video.get("url") or video_id,
                    download=True
                )

                if info is None:

                    logging.warning(
                        f"Download failed or video unavailable: {video_id}"
                    )

                    continue

                # ------------------------------------------------------------------
                # Print selected format information
                # ------------------------------------------------------------------

                requested_formats = info.get(
                    "requested_formats"
                )

                if requested_formats:

                    logging.info(
                        "Selected separate video/audio streams:"
                    )

                    for fmt in requested_formats:

                        logging.info(
                            "  "
                            f"format_id={fmt.get('format_id')} "
                            f"resolution={fmt.get('resolution')} "
                            f"fps={fmt.get('fps')} "
                            f"vcodec={fmt.get('vcodec')} "
                            f"acodec={fmt.get('acodec')} "
                            f"tbr={fmt.get('tbr')}"
                        )

                else:

                    logging.info(
                        "Selected single format: "
                        f"{info.get('format_id')}"
                    )

                # ------------------------------------------------------------------
                # Find downloaded file
                # ------------------------------------------------------------------

                file_path = dl.prepare_filename(info)

                # ------------------------------------------------------------------
                # After merge the extension can become MKV
                # ------------------------------------------------------------------

                if not os.path.exists(file_path):

                    base_path = os.path.splitext(
                        file_path
                    )[0]

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
                            f"Downloaded file was not found: "
                            f"{file_path}"
                        )

                        continue

                # ------------------------------------------------------------------
                # Upload
                # ------------------------------------------------------------------

                if os.path.exists(file_path):

                    logging.info(
                        f"Downloaded file: {file_path}"
                    )

                    upload_ok = upload_to_gdrive(
                        service,
                        folder_id,
                        file_path
                    )

                    # ------------------------------------------------------------------
                    # Delete local file only after successful upload
                    # ------------------------------------------------------------------

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

                else:

                    logging.error(
                        "Final downloaded file does not exist."
                    )

        except Exception as e:

            logging.error(
                f"Error processing {video_id}: {e}"
            )


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":

    setup_environment()

    process_playlist()
