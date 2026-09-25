import os
import re
import html
import time
import asyncio
import requests
from bs4 import BeautifulSoup
import edge_tts
import sys

sys.stdout.reconfigure(line_buffering=True)

# ================= CẤU HÌNH SUPABASE =================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lleeibzegmnycuingzgx.supabase.co")
SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"
)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8"
}

# ================= CẤU HÌNH 4 NGUỒN TRUYỆN MỤC TIÊU =================
# Mỗi nguồn gom số lượng truyện nhất định mỗi lần chạy (mặc định lấy 3-5 truyện mới nhất mỗi nguồn)
SOURCES_CONFIG = [
    {
        "domain": "truyencotich.top",
        "url": "https://truyencotich.top/truyen-co-tich-viet-nam/",
        "category": "Cổ Tích",
        "default_author": "Truyện Cổ Tích Dân Gian",
        "default_cover": "https://images.unsplash.com/photo-1532012164546-f432f2e3777a?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural",
        "limit": 20
    },
    {
        "domain": "eva.vn",
        "url": "https://eva.vn/truyen-co-tich-cho-be-p2607c10.html",
        "category": "Cổ Tích",
        "default_author": "Cổ Tích Cho Bé",
        "default_cover": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural",
        "limit": 20
    },
    {
        "domain": "meocammap.com",
        "url": "https://meocammap.com/",
        "category": "Ngôn Tình",
        "default_author": "Mèo Cầm Mập Tuyển Chọn",
        "default_cover": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural",
        "limit": 20
    },
    {
        "domain": "kenhtruyenfull.com",
        "url": "https://kenhtruyenfull.com/kiem-hiep/",
        "category": "Kiếm Hiệp",
        "default_author": "Kênh Truyện Kiếm Hiệp",
        "default_cover": "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-NamMinhNeural",
        "limit": 20
    },
    {
        "domain": "kenhtruyenfull.com",
        "url": "https://kenhtruyenfull.com/trinh-tham/",
        "category": "Trinh Thám",
        "default_author": "Kỳ Án Trinh Thám",
        "default_cover": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-NamMinhNeural",
        "limit": 20
    }
]

def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

def check_story_exists(title):
    try:
        url = f"{SUPABASE_URL}/rest/v1/audio_stories?title=eq.{requests.utils.quote(title)}&select=id"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
    except Exception:
        pass
    return False

# ================= 1. BỘ QUÉT LINK THEO TỪNG NGUỒN =================
def get_story_links_from_source(source_cfg):
    links = []
    try:
        res = requests.get(source_cfg["url"], headers=HTTP_HEADERS, timeout=12)
        if res.status_code != 200:
            return links
        
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        for a in soup.find_all('a', href=True):
            href = a['href']
            text = clean_text(a.get_text())

            # Chuẩn hóa link tuyệt đối
            if href.startswith('/'):
                domain_prefix = f"https://{source_cfg['domain']}"
                href = domain_prefix + href

            if not href.startswith('http'):
                continue

            # Bỏ qua các liên kết menu rác
            if any(junk in href.lower() for junk in ['#', 'page', 'category', 'tag', 'lien-he', 'chinh-sach', 'login']):
                continue

            # Phân tách logic theo domain
            if "truyencotich.top" in href and len(text) > 10 and href != source_cfg["url"]:
                if href not in [x['url'] for x in links]:
                    links.append({"url": href, "title": text})

            elif "eva.vn" in href and re.search(r'-c\d+a\d+\.html', href) and len(text) > 15:
                if href not in [x['url'] for x in links]:
                    links.append({"url": href, "title": text})

            elif "meocammap.com" in href and len(text) > 10 and href != "https://meocammap.com/":
                if href not in [x['url'] for x in links]:
                    links.append({"url": href, "title": text})

            elif "kenhtruyenfull.com" in href and len(text) > 10 and href != source_cfg["url"]:
                if href not in [x['url'] for x in links]:
                    links.append({"url": href, "title": text})

            if len(links) >= source_cfg["limit"]:
                break

    except Exception as e:
        print(f"      [!] Lỗi quét danh sách từ {source_cfg['url']}: {e}")

    return links

# ================= 2. BỘ BÓC TÁCH NỘI DUNG VĂN BẢN TRUYỆN =================
def extract_story_detail(url, fallback_title):
    try:
        res = requests.get(url, headers=HTTP_HEADERS, timeout=12)
        if res.status_code != 200:
            return fallback_title, None, None

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # Dọn sạch phần tử rác
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form']):
            tag.decompose()
        for tag in soup.find_all(class_=re.compile(r'comment|relate|banner|advert|breadcrumb|sidebar|box-buy')):
            tag.decompose()

        # Tiêu đề
        title_tag = soup.find('h1') or soup.find('title')
        title = clean_text(title_tag.get_text()) if title_tag else fallback_title
        title = re.sub(r'\s*[-|]\s*(Truyện Cổ Tích|Eva\.vn|Mèo Cầm Mập|Kênh Truyện Full).*', '', title, flags=re.IGNORECASE)

        # Ảnh minh họa bìa nếu có trong bài
        cover_image = None
        img_tag = soup.find('img', src=re.compile(r'http|upload|images'))
        if img_tag and img_tag.get('src') and not any(ext in img_tag['src'].lower() for ext in ['icon', 'logo', 'blank']):
            cover_image = img_tag['src']

        # Vùng chứa nội dung chính
        container = (
            soup.find(class_=re.compile(r'entry-content|post-content|content-detail|article-body|chapter-c|chapter-content')) 
            or soup.find('article') 
            or soup.body
        )

        paragraphs = []
        for p in container.find_all(['p', 'div']):
            t = clean_text(p.get_text())
            if len(t) > 35 and not any(k in t.lower() for k in ['nguồn:', 'theo dõi', 'bản quyền', 'click', 'quảng cáo', 'facebook']):
                # Tránh trùng lặp đoạn con
                if not any(t in existing for existing in paragraphs):
                    paragraphs.append(t)

        full_content = "\n".join(paragraphs)
        return title, full_content, cover_image

    except Exception as e:
        print(f"      [!] Lỗi bóc tách bài {url}: {e}")
        return fallback_title, None, None

# ================= 3. BỘ CHUYỂN ĐỔI AUDIO EDGE-TTS =================
async def convert_text_to_audio(text, output_file, voice):
    """
    Trích xuất phần mở đầu câu chuyện (khoảng 5-8 đoạn văn bản) 
    để tạo file MP3 dài 3 - 5 phút nhằm tối ưu thời gian xử lý và dung lượng lưu trữ
    """
    paragraphs = text.split('\n')
    narration_text = " ".join(paragraphs[:8]) if len(paragraphs) > 8 else text
    
    tts = edge_tts.Communicate(narration_text, voice, rate="-3%", pitch="+0Hz")
    await tts.save(output_file)

def upload_to_supabase_storage(local_path, file_name):
    url = f"{SUPABASE_URL}/storage/v1/object/audio-books/{file_name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "audio/mpeg"
    }
    with open(local_path, 'rb') as f:
        requests.post(url, headers=headers, data=f)
    return f"{SUPABASE_URL}/storage/v1/object/public/audio-books/{file_name}"

# ================= 4. QUY TRÌNH THU THẬP VÀ ĐỒNG BỘ CHÍNH =================
async def main():
    print("=== BẮT ĐẦU CÀO TRUYỆN ĐA NGUỒN & TỰ ĐỘNG TẠO AUDIO STREAMING ===")
    total_saved = 0

    for source in SOURCES_CONFIG:
        print(f"\n[*] Đang quét nguồn: {source['domain']} -> {source['category']}")
        links = get_story_links_from_source(source)
        print(f"    Tìm thấy {len(links)} truyện tiềm năng.")

        for item in links:
            url = item["url"]
            fallback_title = item["title"]

            title, content, scraped_cover = extract_story_detail(url, fallback_title)

            if not content or len(content) < 150:
                continue

            if check_story_exists(title):
                print(f"    (-) Đã có: '{title[:40]}...' (Bỏ qua)")
                continue

            print(f"\n    [+] Đang xử lý: {title}")
            description = (content[:220] + "...") if len(content) > 220 else content
            cover_img = scraped_cover if (scraped_cover and scraped_cover.startswith('http')) else source["default_cover"]

            # 1. Lưu vào bảng audio_stories
            story_payload = {
                "title": title,
                "author": source["default_author"],
                "category": source["category"],
                "description": description,
                "cover_image": cover_img,
                "total_chapters": 1
            }
            res_story = requests.post(
                f"{SUPABASE_URL}/rest/v1/audio_stories",
                headers={**HEADERS, "Prefer": "return=representation"},
                json=story_payload
            )

            if res_story.status_code not in [200, 201]:
                print(f"        [!] Lỗi ghi DB: {res_story.text}")
                continue

            story_id = res_story.json()[0]["id"]

            # 2. Tạo giọng đọc AI
            tmp_mp3 = f"temp_{story_id}.mp3"
            print(f"        -> Đang diễn đọc AI bằng giọng {source['voice']}...")
            await convert_text_to_audio(content, tmp_mp3, source["voice"])

            # 3. Tải lên Supabase Storage
            dest_filename = f"story_{story_id}_vol1.mp3"
            print(f"        -> Đang tải audio lên Storage...")
            audio_url = upload_to_supabase_storage(tmp_mp3, dest_filename)

            # 4. Ghi nhận vào audio_chapters
            chap_payload = {
                "story_id": story_id,
                "chapter_number": 1,
                "chapter_title": f"Bản phát thanh: {title}",
                "audio_url": audio_url,
                "content": content
            }
            requests.post(f"{SUPABASE_URL}/rest/v1/audio_chapters", headers=HEADERS, json=chap_payload)

            if os.path.exists(tmp_mp3):
                os.remove(tmp_mp3)

            total_saved += 1
            print(f"        ✔ Thành công! Đã lưu trọn vẹn truyện & Audio lên đài.")
            time.sleep(1.0)

    print(f"\n=== HOÀN TẤT! ĐÃ THÊM MỚI {total_saved} BỘ TRUYỆN AUDIO VÀO MỘNG HOA CÁC ===")

if __name__ == "__main__":
    asyncio.run(main())
