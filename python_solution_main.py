import os
import yt_dlp
from playwright.sync_api import sync_playwright

def generate_youtube_cookies(output_file="youtube_cookies.txt"):
    """
    اجرای مرورگر کروم برای دریافت کوکی‌های یوتوب و عبور از کپچا و ربات‌یاب
    """
    print("🚀 در حال اجرای مرورگر کروم برای دریافت خودکار کوکی‌های یوتوب...")
    
    with sync_playwright() as p:
        # مرورگر به صورت مخفی اجرا می‌شود
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # باز کردن یوتوب
        page.goto("https://www.youtube.com")
        
        print("⏳ در حال صبر برای لود شدن کامل و دور زدن ربات‌یاب یوتوب...")
        page.wait_for_timeout(5000) 
        
        # استخراج کوکی‌ها
        cookies = context.cookies()
        
        # ذخیره کوکی‌ها با فرمت Netscape
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
        print(f"✅ کوکی‌ها با موفقیت دریافت و در {output_file} ذخیره شدند.")

def download_video(video_url):
    cookie_file = "youtube_cookies.txt"
    
    # اول از همه کوکی‌های تازه را می‌گیریم
    generate_youtube_cookies(cookie_file)
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': '%(title)s.%(ext)s',
        'cookiefile': cookie_file,
    }
    
    print("⬇️ در حال دانلود ویدیو...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info_dict)
        print(f"✅ دانلود تمام شد: {filename}")
        return filename

if __name__ == "__main__":
    url = input("🔗 لینک ویدیو یا پلی‌لیست یوتوب را وارد کنید: ")
    downloaded_file = download_video(url)
    
    # بعد از دانلود، کد مربوط به آپلود گوگل درایو خود را اینجا قرار دهید
    print("آماده آپلود به گوگل درایو...")
