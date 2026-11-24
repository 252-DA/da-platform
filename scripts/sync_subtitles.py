"""
Script tạo và đồng bộ hóa phụ đề WebVTT chuẩn xác từng mili-giây cho video Hybrid 4 cảnh.
"""
import asyncio
import json
from pathlib import Path

from worker.config import WorkerSettings
from worker.container import build_file_storage
from worker.services.micro_content_subtitles import build_webvtt_and_timeline
from worker.services.tts_client import EdgeTtsClient


async def main():
    print("=" * 80)
    print("BẮT ĐẦU ĐỒNG BỘ PHỤ ĐỀ WEBVTT CHO VIDEO HYBRID STRAIGHT INSERTION SORT")
    print("=" * 80)

    scenes = [
        {
            "scene_index": 0,
            "title": "Nguyên lý chèn trực tiếp (Straight Insertion Sort)",
            "slide_page": 10,
            "narration": "Thuật toán sắp xếp chèn trực tiếp hoạt động dựa trên nguyên lý chia danh sách làm hai phần: phần đã sắp xếp và phần chưa sắp xếp. Tại mỗi bước lặp, phần tử đầu tiên của phần chưa sắp xếp sẽ được chọn và chèn vào vị trí thích hợp trong phần đã sắp xếp.",
        },
        {
            "scene_index": 1,
            "title": "Minh họa từng bước trên mảng dữ liệu (Full 5-Pass Trace)",
            "slide_page": 11,
            "narration": "Hãy quan sát mảng ví dụ gồm các số: hai mươi ba, bảy mươi tám, bốn mươi lăm, tám, ba mươi hai và năm mươi sáu. Ban đầu, phần tử đầu tiên được xem là đã sắp xếp. Các phần tử kế tiếp lần lượt được so sánh để dời chỗ và chèn vào đúng thứ tự. Quá trình tiếp tục tương tự cho các phần tử tám, ba mươi hai và năm mươi sáu, cho đến khi toàn bộ mảng được sắp xếp hoàn chỉnh theo thứ tự tăng dần.",
        },
        {
            "scene_index": 2,
            "title": "Giải thuật và Mã giả InsertionSort()",
            "slide_page": 17,
            "narration": "Về mặt thuật toán, vòng lặp ngoài duyệt biến current từ vị trí một đến cuối mảng. Giá trị cần chèn được lưu tạm vào biến temp, trong khi biến walker lùi dần để dời các phần tử lớn hơn temp sang phải, và cuối cùng đặt temp vào vị trí thích hợp.",
        },
        {
            "scene_index": 3,
            "title": "Độ phức tạp tính toán của thuật toán",
            "slide_page": 27,
            "narration": "Hiệu năng của thuật toán được đo bằng tổng số phép so sánh và số lần di chuyển. Trong trường hợp xấu nhất, hàm f của n bằng n nhân n cộng một chia hai, tương ứng với độ phức tạp thời gian cấp O n bình phương.",
        },
    ]

    # Thời lượng thực tế từng cảnh trong video ghép (ms):
    # Scene 0: 15.04s = 15040 ms
    # Scene 1: 25.48s = 25480 ms
    # Scene 2: 15.16s = 15160 ms
    # Scene 3: 14.16s = 14160 ms
    scene_durations_ms = [15040, 25480, 15160, 14160]

    # Lấy cues từ TTS client để khớp từng câu nói
    client = EdgeTtsClient()
    scene_cues = []
    speech_durations_ms = []

    print("[1/3] Lấy timestamp phụ đề từ Edge TTS cho từng cảnh...")
    for idx, sc in enumerate(scenes):
        dummy_audio = f"/tmp/dummy_scene_{idx}.mp3"
        res = await client.synthesize_with_cues(sc["narration"], dummy_audio, voice="vi-VN-HoaiMyNeural")
        print(f"  + Cảnh {idx}: {len(res.cues)} cues, audio thực tế: {res.duration_seconds:.2f}s")
        scene_cues.append(res.cues)
        speech_durations_ms.append(int(res.duration_seconds * 1000))

    # Dựng WebVTT chuẩn hóa
    print("[2/3] Xây dựng file WebVTT đồng bộ hoàn hảo theo timeline video...")
    vtt_text, transcript_text, timeline = build_webvtt_and_timeline(
        scenes=scenes,
        scene_durations_ms=scene_durations_ms,
        scene_cues=scene_cues,
        speech_durations_ms=speech_durations_ms,
    )

    vtt_file = Path("/tmp/insertion_sort_hybrid_subtitles.vtt")
    vtt_file.write_text(vtt_text, encoding="utf-8")
    print(f"  + Đã tạo file VTT ({len(vtt_text)} ký tự)")
    print("\nNỘI DUNG WEBVTT ĐỒNG BỘ MỚI:")
    print("-" * 60)
    print(vtt_text)
    print("-" * 60)

    # Tải lên MinIO
    print("\n[3/3] Tải WebVTT lên MinIO và cập nhật Database...")
    cfg = WorkerSettings()
    storage = build_file_storage(cfg)

    # Upload vào cả key mới và key cũ (để ghi đè cache của browser)
    key_new = "micro-content/01a1f94a-71e6-7c70-97a8-eade510d71d2/01a1f973-bf91-741d-9a96-d086704166a8/ai-hybrid-pilot.vtt"
    key_old = "micro-content/01a1f94a-71e6-7c70-97a8-eade510d71d2/01a1f973-bf91-741d-9a96-d086704166a8/ai-cd52a880-585a-4d03-b25d-0c7e12c39123.vtt"

    storage.upload(vtt_file, key_new)
    storage.upload(vtt_file, key_old)
    print("  + Đã upload VTT lên MinIO thành công!")

    # Tạo file SQL để cập nhật DB
    sql_file = Path("/tmp/update_vtt.sql")
    sql_content = f"""
    UPDATE video_assets
    SET vtt_subtitles_key = '{key_new}',
        transcript_text = $transcript${transcript_text}$transcript$,
        scene_timeline = '{json.dumps(timeline)}'::jsonb
    WHERE asset_id = '01a20898-59ea-7341-946c-521264ed931b';
    """
    sql_file.write_text(sql_content, encoding="utf-8")
    print("  + Đã tạo file update SQL:", sql_file)

    print("[HOÀN TẤT] File WebVTT và SQL cập nhật đã sẵn sàng!")


if __name__ == "__main__":
    asyncio.run(main())
