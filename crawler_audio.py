import os
import re
import html
import time
import asyncio
import requests
from bs4 import BeautifulSoup
import edge_tts
import sys
from urllib.parse import urljoin

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

# ================= CẤU HÌNH NGUỒN CÀO =================
# MAX_CHAPTERS_PER_STORY: Giới hạn số chương cào thử nghiệm mỗi truyện để tránh GitHub Actions timeout
MAX_CHAPTERS_PER_STORY = int(os.getenv("MAX_CHAPTERS", 3))

SOURCES_CONFIG = [
    {
        "domain": "truyencotich.top",
        "url": "https://truyencotich.top/truyen-co-tich-viet-nam/",
        "category": "Cổ Tích",
        "default_author": "Truyện Cổ Tích Dân Gian",
        "default_cover": "https://images.unsplash.com/photo-1532012164546-f432f2e3777a?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural",
        "story_limit": 20
    },
    {
        "domain": "eva.vn",
        "url": "https://eva.vn/truyen-co-tich-cho-be-p2607c10.html",
        "category": "Cổ Tích",
        "default_author": "Cổ Tích Cho Bé",
        "default_cover": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural",
        "story_limit": 20
    },
    {
        "domain": "meocammap.com",
        "url": "https://meocammap.com/",
        "category": "Ngôn Tình",
        "default_author": "Mèo Cầm Mập",
        "default_cover": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural",
        "story_limit": 20
    },
    {
        "domain": "kenhtruyenfull.com",
        "url": "https://kenhtruyenfull.com/kiem-hiep/",
        "category": "Kiếm Hiệp",
        "default_author": "Kim Dung & Đa Tác Giả",
        "default_cover": "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-NamMinhNeural",
        "story_limit": 20
    },
    {
        "domain": "kenhtruyenfull.com",
        "url": "https://kenhtruyenfull.com/trinh-tham/",
        "category": "Trinh Thám",
        "default_author": "Trinh Thám Ly Kỳ",
        "default_cover": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-NamMinhNeural",
        "story_limit": 20
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
            return res.json()[0]["id"]
    except Exception:
        pass
    return None

# ================= 1. QUÉT DANH SÁCH BỘ TRUYỆN =================
def get_story_list(source_cfg):
    stories = []
    try:
        res = requests.get(source_cfg["url"], headers=HTTP_HEADERS, timeout=12)
        if res.status_code != 200:
            return stories
        
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        for a in soup.find_all('a', href=True):
            href = urljoin(source_cfg["url"], a['href'])
            title = clean_text(a.get_text())

            if not href.startswith('http') or href == source_cfg["url"]:
                continue

            if any(junk in href.lower() for junk in ['#', 'page', 'category', 'tag', 'lien-he', 'chinh-sach', 'login', 'author']):
                continue

            if len(title) > 8 and not any(s['url'] == href for s in stories):
                stories.append({"url": href, "title": title})

            if len(stories) >= source_cfg["story_limit"]:
                break

    except Exception as e:
        print(f"      [!] Lỗi quét danh mục {source_cfg['url']}: {e}")

    return stories

# ================= 2. BÓC TÁCH CHI TIẾT TRUYỆN & DANH SÁCH CHƯƠNG =================
def extract_story_and_chapters(story_url, fallback_title):
    """
    Truy cập vào trang truyện:
    - Lấy thông tin (Tên, Ảnh bìa, Tóm tắt).
    - Tự động phát hiện xem trang này có Danh sách chương (Chương 1, 2, 3...) hay là 1 bài đọc đơn.
    """
    try:
        res = requests.get(story_url, headers=HTTP_HEADERS, timeout=12)
        if res.status_code != 200:
            return fallback_title, None, None, []

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # Dọn rác
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form']):
            tag.decompose()

        # Tên truyện
        title_tag = soup.find('h1') or soup.find('title')
        title = clean_text(title_tag.get_text()) if title_tag else fallback_title
        title = re.sub(r'\s*[-|]\s*(Truyện Cổ Tích|Eva\.vn|Mèo Cầm Mập|Kênh Truyện Full).*', '', title, flags=re.IGNORECASE)

        # Bìa truyện
        cover_img = None
        img = soup.find('img', src=re.compile(r'http|upload|images'))
        if img and img.get('src') and not any(k in img['src'].lower() for k in ['icon', 'logo', 'blank']):
            cover_img = img['src']

        # Tìm danh sách chương (chương 1, chương 2, chap 1, phần 1, hồi 1...)
        chapters = []
        chap_pattern = re.compile(r'(chương|chap|hồi|phần|tập)\s*\d+', re.IGNORECASE)

        for a in soup.find_all('a', href=True):
            a_text = clean_text(a.get_text())
            chap_href = urljoin(story_url, a['href'])
            
            # Nếu thẻ link có chữ "Chương 1", "Hồi 1", "Phần 1"...
            if chap_pattern.search(a_text) or chap_pattern.search(chap_href):
                if chap_href != story_url and not any(c['url'] == chap_href for c in chapters):
                    chapters.append({
                        "title": a_text if len(a_text) > 3 else f"Chương {len(chapters) + 1}",
                        "url": chap_href
                    })

        # Tóm tắt truyện
        desc_container = soup.find(class_=re.compile(r'desc|gioi-thieu|summary|entry-content')) or soup.body
        desc_paragraphs = [clean_text(p.get_text()) for p in desc_container.find_all('p') if len(clean_text(p.get_text())) > 30]
        description = "\n".join(desc_paragraphs[:3]) if desc_paragraphs else "Nội dung đang được cập nhật."

        # Nếu không có danh sách chương con -> Đây là truyện ngắn (như cổ tích), coi chính trang này là chương 1
        if not chapters:
            full_paragraphs = [clean_text(p.get_text()) for p in desc_container.find_all('p') if len(clean_text(p.get_text())) > 35]
            if full_paragraphs:
                chapters.append({
                    "title": f"Trọn vẹn: {title}",
                    "url": story_url,
                    "preloaded_content": "\n".join(full_paragraphs)
                })

        return title, description, cover_img, chapters

    except Exception as e:
        print(f"      [!] Lỗi bóc tách truyện {story_url}: {e}")
        return fallback_title, None, None, []

# ================= 3. BÓC TÁCH NỘI DUNG VĂN BẢN TRONG 1 CHƯƠNG =================
def extract_chapter_content(chapter_info):
    if "preloaded_content" in chapter_info:
        return chapter_info["preloaded_content"]

    try:
        res = requests.get(chapter_info["url"], headers=HTTP_HEADERS, timeout=12)
        if res.status_code != 200:
            return None

        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form']):
            tag.decompose()

        # Vùng chứa chữ của chương
        content_box = (
            soup.find(class_=re.compile(r'chapter-c|chapter-content|entry-content|content-detail|post-content')) 
            or soup.find('article') 
            or soup.body
        )

        paragraphs = []
        for p in content_box.find_all(['p', 'div']):
            t = clean_text(p.get_text())
            if len(t) > 35 and not any(k in t.lower() for k in ['nguồn:', 'theo dõi', 'bản quyền', 'click', 'quảng cáo', 'facebook']):
                if not any(t in existing for existing in paragraphs):
                    paragraphs.append(t)

        return "\n".join(paragraphs)
    except Exception as e:
        print(f"         [!] Lỗi lấy nội dung chương {chapter_info['url']}: {e}")
        return None

# ================= 4. TẠO AUDIO & UPLOAD SUPABASE =================
async def text_to_audio(text, output_file, voice):
    """Lấy khoảng 6 đoạn văn bản đầu của mỗi chương để tạo file MP3 demo chất lượng cao"""
    paragraphs = text.split('\n')
    narration_text = " ".join(paragraphs[:6]) if len(paragraphs) > 6 else text
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

# ================= 5. CHƯƠNG TRÌNH ĐIỀU PHỐI CHÍNH =================
async def main():
    print("=== BẮT ĐẦU CÀO TRUYỆN ĐA PHẦN/ĐA CHƯƠNG & TẠO AUDIO STREAMING ===")
    total_stories = 0
    total_chapters = 0

    for source in SOURCES_CONFIG:
        print(f"\n=======================================================")
        print(f"[*] QUÉT NGUỒN: {source['domain']} [{source['category']}]")
        print(f"=======================================================")
        
        stories_list = get_story_list(source)
        print(f"-> Tìm thấy {len(stories_list)} bộ truyện tiềm năng.")

        for item in stories_list:
            story_url = item["url"]
            fallback_title = item["title"]

            title, description, cover_img, chapters = extract_story_and_chapters(story_url, fallback_title)
            
            if not chapters:
                print(f"   [-] Không tìm thấy chương nào cho '{title}'. Bỏ qua.")
                continue

            # Kiểm tra xem truyện đã có trên Supabase chưa
            existing_story_id = check_story_exists(title)
            if existing_story_id:
                print(f"   (i) Bộ truyện '{title[:35]}...' đã có sẵn trong DB (ID: {existing_story_id}).")
                story_id = existing_story_id
            else:
                # Tạo mới bộ truyện
                cover = cover_img if (cover_img and cover_img.startswith('http')) else source["default_cover"]
                story_payload = {
                    "title": title,
                    "author": source["default_author"],
                    "category": source["category"],
                    "description": description[:300] + "...",
                    "cover_image": cover,
                    "total_chapters": len(chapters)
                }
                res_story = requests.post(f"{SUPABASE_URL}/rest/v1/audio_stories", headers={**HEADERS, "Prefer": "return=representation"}, json=story_payload)
                if res_story.status_code not in [200, 201]:
                    print(f"   [!] Không thể lưu story: {res_story.text}")
                    continue
                story_id = res_story.json()[0]["id"]
                print(f"\n   [+] TẠO BỘ TRUYỆN: '{title}' (ID: {story_id}, Tổng số chương phát hiện: {len(chapters)})")
                total_stories += 1

            # Lấy chi tiết từng chương (chạy tối đa MAX_CHAPTERS_PER_STORY chương)
            chapters_to_crawl = chapters[:MAX_CHAPTERS_PER_STORY]
            for idx, chap in enumerate(chapters_to_crawl, start=1):
                chap_title = chap["title"]
                print(f"       -> [Chương {idx}/{len(chapters_to_crawl)}] Đang cào: '{chap_title}'...")

                content = extract_chapter_content(chap)
                if not content or len(content) < 100:
                    print(f"          [!] Nội dung chương quá ngắn hoặc không đọc được. Bỏ qua.")
                    continue

                # Tạo Audio MP3 bằng giọng AI Neural
                tmp_mp3 = f"temp_s{story_id}_c{idx}.mp3"
                print(f"          -> Tạo Audio diễn đọc AI ({source['voice']})...")
                await text_to_audio(content, tmp_mp3, source["voice"])

                # Tải lên Supabase Storage
                dest_filename = f"story_{story_id}_chap_{idx}.mp3"
                print(f"          -> Đang tải audio lên bucket 'audio-books'...")
                audio_url = upload_to_supabase_storage(tmp_mp3, dest_filename)

                # Lưu vào audio_chapters
                chap_payload = {
                    "story_id": story_id,
                    "chapter_number": idx,
                    "chapter_title": chap_title,
                    "audio_url": audio_url,
                    "content": content
                }
                requests.post(f"{SUPABASE_URL}/rest/v1/audio_chapters", headers=HEADERS, json=chap_payload)

                if os.path.exists(tmp_mp3):
                    os.remove(tmp_mp3)

                total_chapters += 1
                print(f"          ✔ Đã lưu xong Chương {idx} kèm Audio!")
                time.sleep(1)

    print(f"\n=== HOÀN TẤT! ĐÃ NẠP {total_stories} BỘ TRUYỆN VÀ {total_chapters} TẬP/CHƯƠNG AUDIO ===")

if __name__ == "__main__":
    asyncio.run(main())
