import psycopg2
from pathlib import Path
from worker.config import WorkerSettings
from worker.container import build_file_storage

cfg = WorkerSettings()
storage = build_file_storage(cfg)
local_file = Path("/app/media/insertion_sort_hybrid_pilot.mp4")
key = "micro-content/01a1f94a-71e6-7c70-97a8-eade510d71d2/01a1f973-bf91-741d-9a96-d086704166a8/ai-hybrid-pilot.mp4"

print("[1/2] Đang tải video lên MinIO...")
res = storage.upload(local_file, key)
print("Upload kết quả:", res)

print("[2/2] Cập nhật PostgreSQL database...")
conn = psycopg2.connect("postgresql://postgres:postgres@postgres:5432/chunking")
cur = conn.cursor()

narration = (
    "Hãy quan sát mảng ví dụ gồm các số: hai mươi ba, bảy mươi tám, bốn mươi lăm, tám, ba mươi hai và năm mươi sáu. "
    "Ban đầu, phần tử đầu tiên được xem là đã sắp xếp. Các phần tử kế tiếp lần lượt được so sánh để dời chỗ và chèn vào đúng thứ tự. "
    "Quá trình tiếp tục tương tự cho các phần tử tám, ba mươi hai và năm mươi sáu, cho đến khi toàn bộ mảng được sắp xếp hoàn chỉnh theo thứ tự tăng dần."
)

cur.execute("""
    UPDATE micro_contents
    SET video_duration_ms = 69867,
        video_size_bytes = %s,
        ai_script = jsonb_set(
            ai_script,
            '{scenes,1,narration}',
            to_jsonb(%s::text)
        )
    WHERE micro_content_id = '01a1f973-bf91-741d-9a96-d086704166a8';
""", (local_file.stat().st_size, narration))

import json
timeline = [
    {"scene_index": 0, "title": "Nguyên lý chèn trực tiếp (Straight Insertion Sort)", "slide_page": 10, "start_ms": 0, "end_ms": 15040, "duration_ms": 15040},
    {"scene_index": 1, "title": "Minh họa từng bước trên mảng dữ liệu (Full 5-Pass Trace)", "slide_page": 11, "start_ms": 15040, "end_ms": 40520, "duration_ms": 25480},
    {"scene_index": 2, "title": "Giải thuật và Mã giả InsertionSort()", "slide_page": 17, "start_ms": 40520, "end_ms": 55680, "duration_ms": 15160},
    {"scene_index": 3, "title": "Độ phức tạp tính toán của thuật toán", "slide_page": 27, "start_ms": 55680, "end_ms": 69840, "duration_ms": 14160}
]

cur.execute("""
    UPDATE video_assets
    SET duration_ms = 69867,
        size_bytes = %s,
        ai_script = jsonb_set(
            ai_script,
            '{scenes,1,narration}',
            to_jsonb(%s::text)
        ),
        scene_timeline = %s::jsonb
    WHERE asset_id = '01a20898-59ea-7341-946c-521264ed931b';
""", (local_file.stat().st_size, narration, json.dumps(timeline)))

conn.commit()
cur.close()
conn.close()
print("Cập nhật database thành công 100%!")
