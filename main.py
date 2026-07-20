import os
import sys
import time
import logging
import mimetypes
import yt_dlp
import re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from collections import Counter

# تنظیمات لاگ‌گیری سیستم
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_FOLDER = 'downloads'

def setup_environment():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

# ==========================================
# بخش ارتباط با گوگل درایو
# ==========================================
def get_gdrive_service():
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        logging.warning("اطلاعات ورود به گوگل درایو یافت نشد.")
        return None

    try:
        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret
        )
        creds.refresh(Request())
        return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        logging.error(f"خطا در اتصال به گوگل درایو: {e}")
        return None

def video_exists_in_gdrive(service, folder_id, video_id):
    query = f"'{folder_id}' in parents and name contains '{video_id}' and trashed=false"
    for attempt in range(3):
        try:
            results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute(num_retries=3)
            return len(results.get('files', [])) > 0
        except Exception as e:
            logging.warning(f"خطا در جستجوی فایل در درایو (تلاش {attempt + 1}): {e}")
            time.sleep(2)
    return False

def upload_to_gdrive(service, folder_id, file_path):
    logging.info(f"در حال آپلود فایل به گوگل درایو: {os.path.basename(file_path)}")
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        media = MediaFileUpload(
            file_path, 
            mimetype=mime_type or 'application/octet-stream', 
            resumable=True,
            chunksize=5 * 1024 * 1024
        )
        
        file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
        request = service.files().create(body=file_metadata, media_body=media, fields='id')
        
        response = None
        error_count = 0
        while response is None:
            try:
                status, response = request.next_chunk(num_retries=3)
                if status:
                    logging.info(f"پیشرفت آپلود درایو: {int(status.progress() * 100)}%")
                error_count = 0
            except Exception as e:
                error_count += 1
                logging.warning(f"خطا در آپلود بخش (تلاش {error_count}): {e}")
                if error_count > 5:
                    logging.error("تعداد خطاهای آپلود بیش از حد مجاز شد. آپلود متوقف می‌شود.")
                    return False
                time.sleep(2 ** error_count)
                
        logging.info(f"آپلود با موفقیت انجام شد! شناسه فایل: {response.get('id')}")
        return True
    except Exception as e:
        logging.error(f"خطا در آماده‌سازی آپلود فایل: {e}")
        return False

# ==========================================
# توابع کمکی زمان‌بندی و کار با زیرنویس
# ==========================================
def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int((secs % 1) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d},{millis:03d}"

def parse_time_to_seconds(time_str):
    h, m, s = time_str.split(':')
    s, ms = s.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def read_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().replace('\r\n', '\n').replace('\r', '\n')
    
    blocks = []
    for part in re.split(r'\n\n+', content.strip()):
        lines = part.strip().split('\n')
        if len(lines) >= 2:
            for i, line in enumerate(lines):
                time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
                if time_match and i + 1 < len(lines):
                    text = '\n'.join(lines[i+1:])
                    blocks.append({'start': time_match.group(1), 'end': time_match.group(2), 'text': text})
                    break
    return blocks

def clean_subtitle_text(text):
    text = re.sub(r'[\(\[][\s\S]*?[\)\]]', '', text)
    text = re.sub(r'[\♪\♫]', '', text)
    text = '\n'.join([re.sub(r'^-?\s*[\w\s]+:\s*', '', l).strip() for l in text.split('\n')])
    text = '\n'.join([l for l in text.split('\n') if l.strip() not in ['-', '']])
    return re.sub(r'  +', ' ', text).strip()

def calculate_sync_params(srt_blocks, whisper_data):
    srt_starts = [parse_time_to_seconds(b['start']) for b in srt_blocks]
    whisper_starts = [w[0] for w in whisper_data]
    
    if not srt_starts or not whisper_starts:
        return 1.0, 0.0

    diffs = [round(w - s, 1) for s in srt_starts for w in whisper_starts if -120 < (w - s) < 120]
    if not diffs:
        return 1.0, 0.0
        
    counter = Counter(diffs)
    global_offset = counter.most_common(1)[0][0]
    return 1.0, global_offset

def process_and_translate_subtitle(video_path, srt_path):
    logging.info("شروع پردازش، همگام‌سازی و ترجمه زیرنویس...")
    
    blocks = read_srt(srt_path)
    cleaned_blocks = []
    for b in blocks:
        cl_text = clean_subtitle_text(b['text'])
        if cl_text:
            cleaned_blocks.append({'start': b['start'], 'end': b['end'], 'text': cl_text})

    if not cleaned_blocks:
        logging.warning("متنی پس از پاکسازی زیرنویس باقی نماند.")
        return srt_path

    logging.info("در حال اجرای Whisper برای استخراج زمان‌بندی صدا...")
    try:
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(video_path, beam_size=5, vad_filter=True)
        
        whisper_data = []
        for segment in segments:
            start_time = segment.start
            if segment.words:
                start_time = segment.words[0].start
            whisper_data.append((start_time, segment.end))
    except Exception as e:
        logging.error(f"خطا در Whisper: {e}. از زیرنویس اصلی بدون سینک استفاده می‌شود.")
        whisper_data = []

    scale, offset = 1.0, 0.0
    if whisper_data:
        scale, offset = calculate_sync_params(cleaned_blocks, whisper_data)
        logging.info(f"آفست زمانی محاسبه شده: {offset:+.2f} ثانیه")

    translator = GoogleTranslator(source='en', target='fa')
    synced_fa_blocks = []
    
    logging.info("در حال ترجمه خطوط به فارسی روان...")
    for block in cleaned_blocks:
        start_sec = max(0, scale * parse_time_to_seconds(block['start']) + offset)
        end_sec = max(0, scale * parse_time_to_seconds(block['end']) + offset)
        
        try:
            fa_text = translator.translate(block['text'])
        except Exception as trans_err:
            logging.error(f"خطا در ترجمه خط '{block['text']}': {trans_err}")
            fa_text = block['text']
            
        synced_fa_blocks.append({'start': start_sec, 'end': end_sec, 'text': fa_text})

    for i in range(len(synced_fa_blocks) - 1):
        if synced_fa_blocks[i]['end'] >= synced_fa_blocks[i+1]['start']:
            synced_fa_blocks[i]['end'] = synced_fa_blocks[i+1]['start'] - 0.05

    fa_srt_path = srt_path.replace('.en.srt', '_fa.srt').replace('.srt', '_fa.srt')
    with open(fa_srt_path, 'w', encoding='utf-8') as f:
        for i, block in enumerate(synced_fa_blocks, start=1):
            start_str = format_time(block['start'])
            end_str = format_time(block['end'])
            f.write(f"{i}\n{start_str} --> {end_str}\n{block['text']}\n\n")
            
    return fa_srt_path

# ==========================================
# کنترل‌کننده اصلی و فرآیند پروژه
# ==========================================
def process_playlist():
    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    if not playlist_url or not folder_id:
        logging.error("لینک لیست پخش یا شناسه پوشه یافت نشد.")
        return

    service = get_gdrive_service()
    if not service:
        return

    ydl_opts_flat = {
        'extract_flat': 'in_playlist', 'quiet': True,
        'cookiefile': 'cookies.txt', 'js_runtimes': {'node': {}},
        'extractor_args': {'youtube': ['player_client=android,web,mweb']}
    }

    with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
        logging.info("در حال دریافت اطلاعات لیست پخش...")
        playlist_dict = ydl.extract_info(playlist_url, download=False)
        
        if 'entries' not in playlist_dict:
            logging.error("ویدیویی یافت نشد.")
            return

        for video in playlist_dict['entries']:
            if not video: continue
            video_id = video.get('id')
            
            if video_exists_in_gdrive(service, folder_id, video_id):
                logging.info(f"ویدیو از قبل در درایو موجود است و رد شد: {video_id}")
                continue

            logging.info(f"در حال دانلود ویدیو و زیرنویس انگلیسی: {video_id}")
            
            download_opts = {
                'format': 'bestvideo[vcodec!*=av01]+bestaudio/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s [{video_id}].%(ext)s',
                'merge_output_format': 'mkv',
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'subtitlesformat': 'srt',
                'cookiefile': 'cookies.txt',
                'js_runtimes': {'node': {}},
                'extractor_args': {'youtube': ['player_client=android,web,mweb']},
                'sleep_interval': 5,
                'max_sleep_interval': 10
            }
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as dl:
                    info = dl.extract_info(video.get('url') or video_id, download=True)
                    base_file_path = dl.prepare_filename(info)
                    
                    expected_sub_path = base_file_path.rsplit('.', 1)[0] + '.en.srt'
                    fa_sub_path = None
                    
                    if os.path.exists(expected_sub_path):
                        # همگام‌سازی و ترجمه خودکار زیرنویس به فارسی
                        fa_sub_path = process_and_translate_subtitle(base_file_path, expected_sub_path)
                    else:
                        logging.warning("زیرنویس انگلیسی برای این ویدیو یافت نشد.")

                    # آپلود ویدیو اصلی به گوگل درایو
                    if upload_to_gdrive(service, folder_id, base_file_path):
                        
                        # آپلود فایل زیرنویس SRT به صورت جداگانه
                        if fa_sub_path and os.path.exists(fa_sub_path):
                            logging.info("در حال آپلود فایل متنی زیرنویس...")
                            upload_to_gdrive(service, folder_id, fa_sub_path)
                            
                        # پاک کردن فایل‌های موقت روی سرور گیت‌هاب
                        temp_files = [base_file_path, expected_sub_path]
                        if fa_sub_path:
                            temp_files.append(fa_sub_path)
                        
                        for f in temp_files:
                            if os.path.exists(f): os.remove(f)
                        logging.info("فایل‌های موقت از روی سرور پاک شدند.")
            except Exception as e:
                logging.error(f"خطا در پردازش ویدیو {video_id}: {e}")

if __name__ == "__main__":
    setup_environment()
    process_playlist()
