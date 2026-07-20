import os
import sys
import subprocess
import logging
import mimetypes
import yt_dlp
import re
import json
from collections import Counter
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_FOLDER = 'downloads'

def setup_environment():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

# ==========================================
# توابع گوگل درایو
# ==========================================
def get_gdrive_service():
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        logging.warning("اطلاعات گوگل درایو یافت نشد.")
        return None

    try:
        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret
        )
        creds.refresh(Request())
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logging.error(f"خطا در اتصال به گوگل درایو: {e}")
        return None

def video_exists_in_gdrive(service, folder_id, video_id):
    try:
        query = f"'{folder_id}' in parents and name contains '{video_id}' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        return len(results.get('files', [])) > 0
    except Exception as e:
        logging.error(f"خطا در جستجوی فایل در درایو: {e}")
        return False

def upload_to_gdrive(service, folder_id, file_path):
    logging.info(f"در حال آپلود: {os.path.basename(file_path)}")
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        media = MediaFileUpload(file_path, mimetype=mime_type or 'application/octet-stream', resumable=True)
        file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"آپلود موفق! شناسه: {file.get('id')}")
        return True
    except Exception as e:
        logging.error(f"خطا در آپلود: {e}")
        return False

# ==========================================
# توابع پردازش و همگام‌سازی زیرنویس
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
    
    if not srt_starts or not whisper_starts: return 1.0, 0.0

    diffs = [round(w - s, 1) for s in srt_starts for w in whisper_starts if -120 < (w - s) < 120]
    if not diffs: return 1.0, 0.0
        
    global_offset = Counter(diffs).most_common(1)[0][0]
    return 1.0, global_offset # برای سادگی و جلوگیری از خطای کشیدگی در سرور، فقط آفست را اعمال می‌کنیم

def process_and_translate_subtitle(video_path, srt_path):
    logging.info("شروع پردازش، همگام‌سازی و ترجمه زیرنویس...")
    
    # 1. خواندن و پاکسازی
    blocks = read_srt(srt_path)
    cleaned_blocks = []
    for b in blocks:
        cl_text = clean_subtitle_text(b['text'])
        if cl_text: cleaned_blocks.append({'start': b['start'], 'end': b['end'], 'text': cl_text})

    # 2. استخراج زمان‌بندی با هوش مصنوعی (روی CPU گیت‌هاب)
    logging.info("در حال اجرای Whisper برای استخراج زمان‌بندی صدا...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(video_path, beam_size=5, vad_filter=True)
    
    whisper_data = [(s.words[0].start if s.words else s.start, s.end) for s in segments]
    
    # 3. محاسبه سینک
    _, offset = calculate_sync_params(cleaned_blocks, whisper_data)
    logging.info(f"آفست محاسبه شده: {offset} ثانیه")

    # 4. اعمال زمان‌بندی جدید و ترجمه
    translator = GoogleTranslator(source='en', target='fa')
    synced_fa_blocks = []
    
    logging.info("در حال ترجمه به فارسی...")
    for i, block in enumerate(cleaned_blocks):
        start_sec = max(0, parse_time_to_seconds(block['start']) + offset)
        end_sec = max(0, parse_time_to_seconds(block['end']) + offset)
        
        try:
            # ترجمه متن
            fa_text = translator.translate(block['text'])
        except:
            fa_text = block['text'] # در صورت خطا، همان انگلیسی را می‌گذارد
            
        synced_fa_blocks.append({'start': start_sec, 'end': end_sec, 'text': fa_text})

    # جلوگیری از تداخل زمانی
    for i in range(len(synced_fa_blocks) - 1):
        if synced_fa_blocks[i]['end'] >= synced_fa_blocks[i+1]['start']:
            synced_fa_blocks[i]['end'] = synced_fa_blocks[i+1]['start'] - 0.05

    # 5. ذخیره فایل نهایی
    fa_srt_path = srt_path.replace('.srt', '_fa.srt')
    with open(fa_srt_path, 'w', encoding='utf-8') as f:
        for i, b in enumerate(synced_fa_blocks, 1):
            f.write(f"{i}\n{format_time(b['start'])} --> {format_time(b['end'])}\n{b['text']}\n\n")
            
    return fa_srt_path

def embed_subtitle_to_video(video_path, sub_path):
    logging.info("در حال چسباندن زیرنویس فارسی به ویدیو (Soft-sub)...")
    output_path = video_path.replace('.mkv', '_subbed.mkv').replace('.mp4', '_subbed.mkv')
    
    # استفاده از ffmpeg برای جاسازی زیرنویس بدون رندر مجدد ویدیو (بسیار سریع)
    cmd = [
        'ffmpeg', '-y', '-i', video_path, '-i', sub_path,
        '-c', 'copy', '-c:s', 'srt', 
        '-metadata:s:s:0', 'language=per', '-metadata:s:s:0', 'title=Persian',
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except Exception as e:
        logging.error(f"خطا در چسباندن زیرنویس: {e}")
        return video_path

# ==========================================
# هسته اصلی برنامه
# ==========================================
def process_playlist():
    playlist_url = os.environ.get("YOUTUBE_PLAYLIST_URL")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    if not playlist_url or not folder_id:
        logging.error("لینک لیست پخش یا شناسه پوشه یافت نشد.")
        return

    service = get_gdrive_service()
    if not service: return

    ydl_opts_flat = {
        'extract_flat': 'in_playlist', 'quiet': True,
        'cookiefile': 'cookies.txt', 'js_runtimes': {'node': {}},
        'extractor_args': {'youtube': ['player_client=android,web,mweb']}
    }

    with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)
        
        for video in playlist_dict.get('entries', []):
            if not video: continue
            video_id = video.get('id')
            
            if video_exists_in_gdrive(service, folder_id, video_id):
                logging.info(f"ویدیو تکراری است و رد شد: {video_id}")
                continue

            logging.info(f"در حال دانلود ویدیو و زیرنویس انگلیسی: {video_id}")
            
            # تنظیمات دانلود ویدیو + دانلود خودکار زیرنویس انگلیسی
            download_opts = {
                'format': 'bestvideo[vcodec!*=av01]+bestaudio/best',
                'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s [{video_id}].%(ext)s',
                'merge_output_format': 'mkv',
                'writesubtitles': True,          # دانلود زیرنویس دستی
                'writeautomaticsub': True,       # دانلود زیرنویس خودکار (اگر دستی نبود)
                'subtitleslangs': ['en'],        # فقط انگلیسی
                'subtitlesformat': 'srt',        # فرمت srt
                'cookiefile': 'cookies.txt',
                'js_runtimes': {'node': {}},
                'extractor_args': {'youtube': ['player_client=android,web,mweb']}
            }
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as dl:
                    info = dl.extract_info(video.get('url') or video_id, download=True)
                    base_file_path = dl.prepare_filename(info)
                    
                    # پیدا کردن فایل زیرنویس دانلود شده
                    expected_sub_path = base_file_path.rsplit('.', 1)[0] + '.en.srt'
                    final_video_path = base_file_path
                    
                    if os.path.exists(expected_sub_path):
                        # 1. سینک و ترجمه
                        fa_sub_path = process_and_translate_subtitle(base_file_path, expected_sub_path)
                        # 2. چسباندن به ویدیو
                        final_video_path = embed_subtitle_to_video(base_file_path, fa_sub_path)
                    else:
                        logging.warning("زیرنویس انگلیسی برای این ویدیو یافت نشد. ویدیو بدون زیرنویس آپلود می‌شود.")

                    # آپلود فایل نهایی
                    if upload_to_gdrive(service, folder_id, final_video_path):
                        # پاکسازی فایل‌های موقت
                        for f in [base_file_path, final_video_path, expected_sub_path, expected_sub_path.replace('.srt', '_fa.srt')]:
                            if os.path.exists(f): os.remove(f)
                        logging.info("فایل‌ها از روی سرور پاک شدند.")
                        
            except Exception as e:
                logging.error(f"خطا در پردازش ویدیو {video_id}: {e}")

if __name__ == "__main__":
    setup_environment()
    process_playlist()
