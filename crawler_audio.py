import os
import re
import html
import asyncio
import requests
from bs4 import BeautifulSoup
import edge_tts

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# ================= DANH MỤC NGUỒN CÀO TRUYỆN MẪU THỰC TẾ =================
# Bạn có thể bổ sung thêm nhiều URL truyện chữ vào danh sách này
TARGET_SOURCES = [
    # 1. Cổ Tích Dân Gian
    {
        "url": "https://thegioicotich.vn/truyen-co-tich-viet-nam/cay-khe/",
        "category": "Cổ Tích",
        "default_title": "Sự Tích Cây Khế (Ăn Khế Trả Vàng)",
        "default_author": "Truyện Cổ Tích Dân Gian",
        "cover": "https://images.unsplash.com/photo-1532012164546-f432f2e3777a?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural"
    },
    {
        "url": "https://thegioicotich.vn/truyen-co-tich-viet-nam/tam-cam/",
        "category": "Cổ Tích",
        "default_title": "Truyện Cổ Tích Tấm Cám",
        "default_author": "Truyện Dân Gian Việt Nam",
        "cover": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural"
    },
    # 2. Ngôn Tình
    {
        "url": "https://thegioicotich.vn/truyen-co-tich-viet-nam/su-tich-trau-cau/",
        "category": "Ngôn Tình",
        "default_title": "Sự Tích Trầu Cau (Tình Nghĩa Vợ Chồng)",
        "default_author": "Cổ Tích Tình Duyên",
        "cover": "https://images.unsplash.com/photo-1518895949257-7621c3c786d7?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-HoaiMyNeural"
    },
    # 3. Trinh Thám Kỳ Án
    {
        "url": "https://thegioicotich.vn/truyen-co-tich-viet-nam/vu-an-trai-dua/",
        "category": "Trinh Thám",
        "default_title": "Bao Công Xử Án: Kỳ Án Trái Dưa",
        "default_author": "Kỳ Án Xưa",
        "cover": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-NamMinhNeural"
    },
    # 4. Kiếm Hiệp Dã Sử
    {
        "url": "https://thegioicotich.vn/truyen-truyen-thuyet/thanh-giong/",
        "category": "Kiếm Hiệp",
        "default_title": "Huyền Thoại Thánh Gióng Phá Giặc Ân",
        "default_author": "Truyền Thuyết Anh Hùng",
        "cover": "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80",
        "voice": "vi-VN-NamMinhNeural"
    }
]

def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

def scrape_story_content(url):
    """Cào tiêu đề và toàn bộ văn bản của câu chuyện từ link web"""
    try:
        res = requests.get(url, headers=HTTP_HEADERS, timeout=12)
        if res.status_code != 200:
            return None, None
        
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # Dọn rác
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form']):
            tag.decompose()

        # Tìm tiêu đề
        title_tag = soup.find('h1') or soup.find('title')
        title = clean_text(title_tag.get_text()) if title_tag else "Câu chuyện tuyển chọn"
        title = re.sub(r'\s*-\s*Thế giới cổ tích.*', '', title, flags=re.IGNORECASE)

        # Tìm vùng nội dung chính
        container = soup.find(class_=re.compile(r'entry-content|post-content|content-detail|article-body')) or soup.find('article') or soup.body
        paragraphs = []
        for p in container.find_all('p'):
            t = clean_text(p.get_text())
            if len(t) > 35 and not any(k in t.lower() for k in ['nguồn:', 'theo dõi', 'bản quyền', 'click']):
                paragraphs.append(t)

        full_content = "\n".join(paragraphs)
        return title, full_content
    except Exception as e:
        print(f"      [!] Lỗi cào link {url}: {e}")
        return None, None

async def text_to_mp3(text, filepath, voice):
    """Giới hạn độ dài đoạn diễn đọc demo để tạo file nhanh và chuẩn"""
    # Lấy khoảng 3-5 đoạn đầu để file mp3 nhẹ (~2-3 phút), tối ưu thời gian chạy
    paragraphs = text.split('\n')
    shortened_text = " ".join(paragraphs[:6]) if len(paragraphs) > 6 else text
    
    tts = edge_tts.Communicate(shortened_text, voice, rate="-3%", pitch="+0Hz")
    await tts.save(filepath)

def upload_mp3_to_storage(local_path, file_name):
    """Tải file MP3 lên bucket 'audio-books' trên Supabase"""
    url = f"{SUPABASE_URL}/storage/v1/object/audio-books/{file_name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "audio/mpeg"
    }
    with open(local_path, 'rb') as f:
        requests.post(url, headers=headers, data=f)
    return f"{SUPABASE_URL}/storage/v1/object/public/audio-books/{file_name}"

async def main():
    print("=== BẮT ĐẦU CÀO TRUYỆN TỪ CÁC NGUỒN WEB & TẠO AUDIO ===")
    
    for item in TARGET_SOURCES:
        print(f"\n[*] Đang cào nguồn: {item['url']} [{item['category']}]")
        scraped_title, scraped_content = scrape_story_content(item['url'])
        
        title = scraped_title or item["default_title"]
        content = scraped_content if (scraped_content and len(scraped_content) > 100) else "Nội dung câu chuyện đang được cập nhật."
        author = item["default_author"]
        description = (content[:220] + "...") if len(content) > 220 else content

        # 1. Lưu thông tin bộ truyện vào bảng audio_stories
        story_payload = {
            "title": title,
            "author": author,
            "category": item["category"],
            "description": description,
            "cover_image": item["cover"],
            "total_chapters": 1
        }
        res_story = requests.post(
            f"{SUPABASE_URL}/rest/v1/audio_stories", 
            headers={**HEADERS, "Prefer": "return=representation"}, 
            json=story_payload
        )
        
        if res_story.status_code not in [200, 201]:
            print(f"   [!] Lỗi ghi story: {res_story.text}")
            continue

        story_id = res_story.json()[0]["id"]
        print(f"   ✔ Đã lưu truyện vào DB: ID {story_id} - '{title}'")

        # 2. Tạo giọng đọc AI cho chương truyện
        tmp_mp3 = f"temp_story_{story_id}.mp3"
        print(f"   -> Đang diễn đọc AI bằng giọng {item['voice']}...")
        await text_to_mp3(content, tmp_mp3, item["voice"])

        # 3. Tải lên Supabase Storage
        dest_filename = f"story_{story_id}_full.mp3"
        print(f"   -> Đang tải audio lên Storage: {dest_filename}...")
        public_audio_url = upload_mp3_to_storage(tmp_mp3, dest_filename)

        # 4. Ghi nhận chương vào audio_chapters
        chap_payload = {
            "story_id": story_id,
            "chapter_number": 1,
            "chapter_title": f"Trọn vẹn tác phẩm: {title}",
            "audio_url": public_audio_url,
            "content": content
        }
        res_chap = requests.post(f"{SUPABASE_URL}/rest/v1/audio_chapters", headers=HEADERS, json=chap_payload)
        
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)

        print(f"   ✔ Hoàn tất toàn bộ truyện '{title}' (Audio URL sẵn sàng)")

    print("\n=== HOÀN TẤT THU THẬP ĐA NGUỒN VÀ ĐỒNG BỘ SUPABASE ===")

if __name__ == "__main__":
    asyncio.run(main())
