import os
import asyncio
import requests
import edge_tts

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lleeibzegmnycuingzgx.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Danh mục khởi tạo 4 thể loại chính
STORIES_DATA = [
    {
        "title": "Từng Có Người Yêu Tôi Như Sinh Mệnh",
        "author": "Thư Nghi",
        "category": "Ngôn Tình",
        "cover_image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "description": "Bản tình ca đầy khắc khoải tại thành phố cảng Odessa tuyết trắng giữa cô sinh viên violin An Tôn Nghiêm và chàng trai phong trần Tôn Gia Ngộ.",
        "voice": "vi-VN-HoaiMyNeural",
        "chapters": [
            {
                "number": 1,
                "title": "Tập 1: Mùa đông Odessa tuyết trắng",
                "content": "Tuyết rơi dày đặc trên những con phố cổ kính của thành phố cảng Odessa xinh đẹp. Tôi ôm chặt cây đàn vĩ cầm trong vạt áo dạ, bước vội qua làn gió buốt giá cắt da cắt thịt. Tôi không hề hay biết rằng, bước ngoặt định mệnh của cuộc đời mình sắp sửa bắt đầu khi cánh cửa tiệm cà phê nhỏ ấm áp ấy được đẩy mở ra. Bên ngoài trời lạnh thấu xương, nhưng mùi hương cà phê rang mộc và tiếng nhạc jazz cổ điển bỗng xua tan đi tất cả muộn phiền của những ngày xa xứ."
            }
        ]
    },
    {
        "title": "Tiếu Ngạo Giang Hồ: Khúc Ca Khải Hoàn",
        "author": "Kim Dung",
        "category": "Kiếm Hiệp",
        "cover_image": "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80",
        "description": "Pho kiếm hiệp hào hùng xoay quanh Lệnh Hồ Xung. Giữa vòng xoáy ân oán giang hồ và những âm mưu tranh quyền đoạt vị, khúc Tiếu Ngạo Giang Hồ vẫn vang lên đầy kiêu hãnh.",
        "voice": "vi-VN-NamMinhNeural",
        "chapters": [
            {
                "number": 1,
                "title": "Hồi 1: Diệt Môn Họa Khởi",
                "content": "Mưa gió biên ải nổi lên cuồn cuộn mịt mù khắp góc trời phía Nam. Phúc Uy tiêu cục lừng lẫy bấy lâu bỗng chốc rơi vào thảm cảnh diệt môn đẫm máu bởi kiếm pháp tàn độc khôn lường của phái Thanh Thành. Giữa đêm đen tĩnh mịch, chỉ còn nghe tiếng vó ngựa dồn dập báo hiệu một trường huyết vũ phong ba sắp sửa quét qua toàn cõi võ lâm trung nguyên."
            }
        ]
    },
    {
        "title": "Kỳ Án Chuyến Tàu Tốc Hành Phương Đông",
        "author": "Agatha Christie",
        "category": "Trinh Thám",
        "cover_image": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=600&q=80",
        "description": "Vụ án mạng bí ẩn trong khoang tàu khóa kín giữa đụn tuyết Balkan hoang vu không để lại bất kỳ dấu vết nào.",
        "voice": "vi-VN-NamMinhNeural",
        "chapters": [
            {
                "number": 1,
                "title": "Hồi 1: Mười hai vết dao trong đêm tuyết",
                "content": "Còi tàu thét lên xé toạc màn đêm u tịch khi đoàn tàu bị mắc kẹt hoàn toàn giữa đụn tuyết khổng lồ không lối thoát. Và trong khoang số hai, thi thể của Ratchett nằm bất động với đúng mười hai nhát dao chí mạng. Cửa khoang bị khóa trái từ bên trong. Không một dấu chân nào in trên nền tuyết trắng xóa bên ngoài toa xe."
            }
        ]
    },
    {
        "title": "Sự Tích Cây Vú Sữa",
        "author": "Truyện Dân Gian Việt Nam",
        "category": "Cổ Tích",
        "cover_image": "https://images.unsplash.com/photo-1532012164546-f432f2e3777a?auto=format&fit=crop&w=600&q=80",
        "description": "Câu chuyện cảm động sâu sắc về tình mẫu tử thiêng liêng và lòng hiếu thảo của người con dành cho người mẹ hiền.",
        "voice": "vi-VN-HoaiMyNeural",
        "chapters": [
            {
                "number": 1,
                "title": "Trọn vẹn: Tình mẫu tử bao la",
                "content": "Ngày xưa, có một cậu bé vì ham chơi bị mẹ mắng nên đã giận dỗi vùng vằng bỏ nhà ra đi. Cậu lang thang khắp nơi chốn, đói rách cơ cực mà chẳng một ai đoái hoài giúp đỡ. Một ngày nọ, vừa kiệt sức vừa nhớ mẹ da diết, cậu lần tìm đường trở về căn nhà xưa bên lũy tre làng. Nhưng cảnh còn người mất, người mẹ vì khóc thương con mòn mỏi đã kiệt sức hóa thành một cây xanh tươi tốt giữa vườn. Khi cậu bé ôm lấy thân cây òa khóc nức nở, thân cây rung rinh trút xuống những trái ngọt thơm ngon đẫm dòng sữa trắng mát lành như dòng sữa mẹ năm nào."
            }
        ]
    }
]

async def text_to_mp3(text, filepath, voice):
    tts = edge_tts.Communicate(text, voice, rate="-3%", pitch="+0Hz")
    await tts.save(filepath)

def upload_mp3_to_storage(local_path, file_name):
    url = f"{SUPABASE_URL}/storage/v1/object/audio-books/{file_name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "audio/mpeg"
    }
    with open(local_path, 'rb') as f:
        res = requests.post(url, headers=headers, data=f)
    return f"{SUPABASE_URL}/storage/v1/object/public/audio-books/{file_name}"

async def main():
    print("=== BẮT ĐẦU TẠO DỮ LIỆU AUDIO VÀ LƯU VÀO SUPABASE ===")
    for story in STORIES_DATA:
        print(f"\n[*] Xử lý bộ truyện: {story['title']} [{story['category']}]")
        
        # Lưu vào audio_stories
        story_payload = {
            "title": story["title"],
            "author": story["author"],
            "category": story["category"],
            "description": story["description"],
            "cover_image": story["cover_image"],
            "total_chapters": len(story["chapters"])
        }
        res = requests.post(f"{SUPABASE_URL}/rest/v1/audio_stories", headers={**HEADERS, "Prefer": "return=representation"}, json=story_payload)
        if res.status_code not in [200, 201]:
            print(f"   [!] Lỗi ghi story: {res.text}")
            continue
            
        story_id = res.json()[0]["id"]
        
        # Diễn đọc từng chương và tải lên Storage
        for chap in story["chapters"]:
            print(f"   -> Đang diễn đọc AI ({story['voice']}): {chap['title']}...")
            tmp_file = f"temp_{story_id}_{chap['number']}.mp3"
            await text_to_mp3(chap["content"], tmp_file, story["voice"])
            
            dest_file = f"story_{story_id}_chap_{chap['number']}.mp3"
            print(f"   -> Đang tải file lên Supabase Storage...")
            audio_url = upload_mp3_to_storage(tmp_file, dest_file)
            
            # Ghi vào audio_chapters
            chap_payload = {
                "story_id": story_id,
                "chapter_number": chap["number"],
                "chapter_title": chap["title"],
                "audio_url": audio_url,
                "content": chap["content"]
            }
            requests.post(f"{SUPABASE_URL}/rest/v1/audio_chapters", headers=HEADERS, json=chap_payload)
            
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            print(f"   ✔ Đã lưu chương {chap['number']} thành công!")

    print("\n=== HOÀN TẤT ĐỒNG BỘ DỮ LIỆU AUDIO TRUYỆN ===")

if __name__ == "__main__":
    asyncio.run(main())
