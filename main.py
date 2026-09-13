# ==============================================================================
# 📝 یادداشت‌های فنی و تاریخچه آزمون و خطاها
# ------------------------------------------------------------------------------
# ۱. مشکل Watch Later:
#    این لیست پخش خصوصی است و برنامه بدون احراز هویت کامل به آن دسترسی ندارد.
#    راه حل: استفاده از یک لیست پخش عمومی یا Unlisted.
#
# ۲. مشکل GitHub Actions & State:
#    فایل downloaded_videos.txt بعد از اتمام هر اجرای GitHub حذف می‌شد.
#    راه حل: بررسی مستقیم داخل Google Drive برای پیدا کردن فایل‌ها بر اساس video_id.
#
# ۳. مسدودسازی IPهای GitHub توسط YouTube:
#    سرورهای GitHub ممکن است به دلیل حجم درخواست بالا با محدودیت مواجه شوند.
#    راه حل: استفاده از Cookie مرورگر واقعی کاربر.
#
# ۴. چالش JavaScript (EJS):
#    YouTube برای بعضی درخواست‌ها نیاز به حل JavaScript challenge دارد.
#    راه حل: نصب yt-dlp[default] و استفاده از Node.js.
#
# ۵. مشکل جدید YouTube / SABR:
#    بعضی clientها دیگر URL مستقیم فرمت‌های باکیفیت را برنمی‌گردانند.
#    برای همین از default + web_embedded استفاده می‌کنیم.
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
# تنظیمات لاگ‌گیری
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ==============================================================================
# تنظیمات اصلی
# ==============================================================================

DOWNLOAD_FOLDER = 'downloads'
COOKIE_FILE = 'cookies.txt'


# ==============================================================================
# ساخت پوشه دانلود
# ==============================================================================

def setup_environment():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    logging.info(f"پوشه دانلود آماده است: {DOWNLOAD_FOLDER}")


# ==============================================================================
# اتصال به Google Drive
# ==============================================================================

def get_gdrive_service():
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logging.warning("اطلاعات Google Drive یافت نشد.")
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
            'drive',
            'v3',
            credentials=creds
        )

        logging.info("اتصال به Google Drive موفق بود.")
        return service

    except Exception as e:
        logging.error(f"خطا در اتصال به Google Drive: {e}")
        return None


# ==============================================================================
# بررسی وجود ویدیو در Google Drive
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
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        return len(items) > 0

    except Exception as e:
        logging.error(f"خطا در جستجوی فایل در Google Drive: {e}")
        return False


# ==============================================================================
# آپلود فایل به Google Drive
# ==============================================================================

def upload_to_gdrive(service, folder_id, file_path):

    logging.info(
        f"در حال آپلود فایل به Google Drive: "
        f"{os.path.basename(file_path)}"
    )

    try:

        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }

        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type is None:
            mime_type = 'application/octet-stream'

        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True
        )

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        logging.info(
            f"آپلود موفق بود. "
            f"شناسه فایل: {file.get('id')}"
        )

        return True

    except Exception as e:

        logging.error(
            f"خطا در آپلود فایل به Google Drive: {e}"
        )

        return False


# ==============================================================================
# پردازش Playlist
# ==============================================================================

def process_playlist():

    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    if not playlist_url:
        logging.error(
            "متغیر YOUTUBE_PLAYLIST_URL پیدا نشد."
        )
        return

    if not folder_id:
        logging.error(
            "متغیر GDRIVE_FOLDER_ID پیدا نشد."
        )
        return

    # --------------------------------------------------------------------------
    # اتصال به Google Drive
    # --------------------------------------------------------------------------

    service = get_gdrive_service()

    if not service:
        return

    # --------------------------------------------------------------------------
    # بررسی Cookie
    # --------------------------------------------------------------------------

    if not os.path.exists(COOKIE_FILE):

        logging.warning(
            f"فایل Cookie با نام {COOKIE_FILE} پیدا نشد."
        )

        logging.warning(
            "ممکن است YouTube درخواست‌ها را محدود کند."
        )

    else:

        logging.info(
            f"فایل Cookie پیدا شد: {COOKIE_FILE}"
        )

    # ==============================================================================
    # تنظیمات استخراج Playlist
    # ==============================================================================

    ydl_opts = {

        # گرفتن اطلاعات ویدیوها بدون دانلود
        'extract_flat': 'in_playlist',

        'quiet': True,

        # استفاده از Cookie
        'cookiefile':
            COOKIE_FILE
            if os.path.exists(COOKIE_FILE)
            else None,

        # استفاده از Node برای JS challenge
        'js_runtimes': {
            'node': {}
        },

        # ----------------------------------------------------------------------
        # تغییر مهم:
        #
        # قبلاً:
        # player_client=tv,android,web
        #
        # اکنون:
        # player_client=default,web_embedded
        # ----------------------------------------------------------------------

        'extractor_args': {
            'youtube': [
                'player_client=default,web_embedded'
            ]
        }
    }

    # ==============================================================================
    # خواندن Playlist
    # ==============================================================================

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        logging.info(
            "در حال دریافت اطلاعات Playlist..."
        )

        try:

            playlist_dict = ydl.extract_info(
                playlist_url,
                download=False
            )

        except Exception as e:

            logging.error(
                f"خطا در دریافت Playlist: {e}"
            )

            return

        # ----------------------------------------------------------------------
        # بررسی Playlist
        # ----------------------------------------------------------------------

        if not playlist_dict:

            logging.error(
                "اطلاعات Playlist دریافت نشد."
            )

            return

        if 'entries' not in playlist_dict:

            logging.error(
                "هیچ ویدیویی در Playlist پیدا نشد."
            )

            return

        # ==============================================================================
        # پردازش تک تک ویدیوها
        # ==============================================================================

        for video in playlist_dict['entries']:

            if not video:
                continue

            video_id = video.get('id')

            if not video_id:
                continue

            # ------------------------------------------------------------------
            # بررسی وجود قبلی در Google Drive
            # ------------------------------------------------------------------

            if video_exists_in_gdrive(
                service,
                folder_id,
                video_id
            ):

                logging.info(
                    f"این ویدیو قبلاً در Google Drive وجود دارد و رد شد: "
                    f"{video_id}"
                )

                continue

            # ------------------------------------------------------------------
            # شروع دانلود
            # ------------------------------------------------------------------

            logging.info(
                f"در حال دانلود ویدیوی جدید: {video_id}"
            )

            # ==============================================================================
            # تنظیمات دانلود
            # ==============================================================================

            download_opts = {

                # ------------------------------------------------------------------
                # فرمت دانلود
                #
                # قبلاً:
                # bestvideo[vcodec!*=av01]+bestaudio/best
                #
                # اکنون:
                # bestvideo+bestaudio/best
                #
                # یعنی محدودیت AV1 حذف شده و yt-dlp خودش بهترین ترکیب موجود
                # را انتخاب می‌کند.
                # ------------------------------------------------------------------

                'format':
                    'bestvideo+bestaudio/best',

                # ------------------------------------------------------------------
                # نام فایل
                # ------------------------------------------------------------------

                'outtmpl':
                    f'{DOWNLOAD_FOLDER}/%(title)s [{video_id}].%(ext)s',

                # ------------------------------------------------------------------
                # خروجی نهایی MKV
                # ------------------------------------------------------------------

                'merge_output_format':
                    'mkv',

                # ------------------------------------------------------------------
                # Cookie
                # ------------------------------------------------------------------

                'cookiefile':
                    COOKIE_FILE
                    if os.path.exists(COOKIE_FILE)
                    else None,

                # ------------------------------------------------------------------
                # JavaScript runtime
                # ------------------------------------------------------------------

                'js_runtimes': {
                    'node': {}
                },

                # ------------------------------------------------------------------
                # Client جدید YouTube
                # ------------------------------------------------------------------

                'extractor_args': {
                    'youtube': [
                        'player_client=default,web_embedded'
                    ]
                },

                # ------------------------------------------------------------------
                # فاصله بین دانلودها برای کاهش احتمال محدود شدن
                # ------------------------------------------------------------------

                'sleep_interval': 5,

                'max_sleep_interval': 15,

                # ------------------------------------------------------------------
                # اگر یک ویدیو مشکل داشت، کل برنامه متوقف نشود
                # ------------------------------------------------------------------

                'ignoreerrors': True
            }

            # ==============================================================================
            # دانلود ویدیو
            # ==============================================================================

            try:

                with yt_dlp.YoutubeDL(download_opts) as dl:

                    info = dl.extract_info(
                        video.get('url') or video_id,
                        download=True
                    )

                    # ------------------------------------------------------------------
                    # اگر دانلود انجام نشد
                    # ------------------------------------------------------------------

                    if info is None:

                        logging.warning(
                            f"امکان دانلود ویدیو وجود ندارد: {video_id}"
                        )

                        continue

                    # ------------------------------------------------------------------
                    # پیدا کردن مسیر فایل دانلود شده
                    # ------------------------------------------------------------------

                    file_path = dl.prepare_filename(info)

                    # ------------------------------------------------------------------
                    # گاهی بعد از Merge پسوند فایل به MKV تغییر می‌کند
                    # ------------------------------------------------------------------

                    if not os.path.exists(file_path):

                        base_path = os.path.splitext(
                            file_path
                        )[0]

                        mkv_path = base_path + '.mkv'

                        if os.path.exists(mkv_path):

                            file_path = mkv_path

                    # ------------------------------------------------------------------
                    # بررسی وجود فایل
                    # ------------------------------------------------------------------

                    if os.path.exists(file_path):

                        logging.info(
                            f"فایل دانلود شد: {file_path}"
                        )

                        # --------------------------------------------------------------
                        # آپلود به Google Drive
                        # --------------------------------------------------------------

                        upload_success = upload_to_gdrive(
                            service,
                            folder_id,
                            file_path
                        )

                        # --------------------------------------------------------------
                        # حذف فایل بعد از آپلود موفق
                        # --------------------------------------------------------------

                        if upload_success:

                            try:

                                os.remove(file_path)

                                logging.info(
                                    "فایل بعد از آپلود موفق از سرور حذف شد."
                                )

                            except Exception as delete_error:

                                logging.warning(
                                    f"حذف فایل ممکن نبود: {delete_error}"
                                )

                    else:

                        logging.error(
                            f"فایل دانلود شده پیدا نشد: {file_path}"
                        )

            except Exception as e:

                logging.error(
                    f"خطا در پردازش ویدیو {video_id}: {e}"
                )


# ==============================================================================
# اجرای برنامه
# ==============================================================================

if __name__ == "__main__":

    setup_environment()

    process_playlist()
