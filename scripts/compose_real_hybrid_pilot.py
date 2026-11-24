"""
Script ghép nối video Hybrid thực tế cho bài mẫu Straight Insertion Sort (Phiên bản Đầy đủ 5 Pass):
- Cảnh 0: Slide 10 (Nguyên lý chèn trực tiếp) + Audio gốc (14.64s)
- Cảnh 1: Clip Manim 5-Pass InsertionSortScene2 (20.56s) + Audio TTS Hoài My mới (25.06s)
- Cảnh 2: Slide 17 (Giải thuật & Mã giả) + Audio gốc (14.76s)
- Cảnh 3: Slide 27 (Độ phức tạp thời gian) + Audio gốc (13.76s)
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Thêm path worker
sys.path.insert(0, "/app/worker")
sys.path.insert(0, "/app/packages-ai/src")
sys.path.insert(0, "/app")

from worker.services.video_composer import SceneMedia, VideoComposer


def run_cmd(cmd: list[str]) -> str:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return res.stdout


def probe_file(media_path: str) -> dict:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        media_path
    ]
    raw = run_cmd(cmd)
    return json.loads(raw)


async def main():
    print("=" * 80)
    print("BẮT ĐẦU GHÉP NỐI VIDEO HYBRID 5-PASS: STRAIGHT INSERTION SORT")
    print("=" * 80)

    work_dir = Path("/tmp/hybrid_pilot_workspace")
    work_dir.mkdir(parents=True, exist_ok=True)
    pilot_mp4 = "/tmp/current_pilot.mp4"
    manim_clip = "/tmp/InsertionSortScene2.mp4"
    audio_1_new = "/tmp/audio_scene2_new.mp3"

    print("[1/4] Chuẩn bị tài nguyên các cảnh...")

    # Cảnh 0: 0 -> 14.64s
    audio_0 = str(work_dir / "audio_0.mp3")
    slide_0 = str(work_dir / "slide_0.png")
    if not os.path.exists(slide_0):
        run_cmd(["ffmpeg", "-y", "-ss", "5.0", "-i", pilot_mp4, "-frames:v", "1", slide_0])
    if not os.path.exists(audio_0):
        run_cmd(["ffmpeg", "-y", "-ss", "0", "-t", "14.64", "-i", pilot_mp4, "-vn", "-c:a", "libmp3lame", "-b:a", "192k", audio_0])

    # Cảnh 1: Clip Manim 5-Pass (20.56s) + Audio mới (25.06s)
    # Slide 1 dùng làm ảnh fallback nếu cần
    slide_1 = str(work_dir / "slide_1.png")
    if not os.path.exists(slide_1):
        run_cmd(["ffmpeg", "-y", "-ss", "20.0", "-i", pilot_mp4, "-frames:v", "1", slide_1])

    # Cảnh 2: 31.80 -> 46.56s (duration 14.76s)
    audio_2 = str(work_dir / "audio_2.mp3")
    slide_2 = str(work_dir / "slide_2.png")
    if not os.path.exists(slide_2):
        run_cmd(["ffmpeg", "-y", "-ss", "38.0", "-i", pilot_mp4, "-frames:v", "1", slide_2])
    if not os.path.exists(audio_2):
        run_cmd(["ffmpeg", "-y", "-ss", "31.80", "-t", "14.76", "-i", pilot_mp4, "-vn", "-c:a", "libmp3lame", "-b:a", "192k", audio_2])

    # Cảnh 3: 46.56 -> 60.32s (duration 13.76s)
    audio_3 = str(work_dir / "audio_3.mp3")
    slide_3 = str(work_dir / "slide_3.png")
    if not os.path.exists(slide_3):
        run_cmd(["ffmpeg", "-y", "-ss", "52.0", "-i", pilot_mp4, "-frames:v", "1", slide_3])
    if not os.path.exists(audio_3):
        run_cmd(["ffmpeg", "-y", "-ss", "46.56", "-t", "13.76", "-i", pilot_mp4, "-vn", "-c:a", "libmp3lame", "-b:a", "192k", audio_3])

    # Lấy chính xác thời lượng audio mới của Cảnh 1
    meta_a1 = probe_file(audio_1_new)
    dur_a1 = float(meta_a1["format"]["duration"])
    print(f"  + Thời lượng Audio Cảnh 1 (Hoài My TTS mới): {dur_a1:.2f}s")

    print("[2/4] Khởi tạo SceneMedia danh sách 4 cảnh:")
    print("  - Cảnh 0: Slide tĩnh 10 (14.64s)")
    print(f"  - Cảnh 1: Clip Manim 5-Pass (20.56s) -> ghép Audio Hoài My ({dur_a1:.2f}s)")
    print("  - Cảnh 2: Slide tĩnh 17 (14.76s)")
    print("  - Cảnh 3: Slide tĩnh 27 (13.76s)")

    scenes = [
        SceneMedia(slide_image_path=slide_0, audio_path=audio_0, duration_seconds=14.64),
        SceneMedia(slide_image_path=slide_1, audio_path=audio_1_new, duration_seconds=dur_a1, video_clip_path=manim_clip),
        SceneMedia(slide_image_path=slide_2, audio_path=audio_2, duration_seconds=14.76),
        SceneMedia(slide_image_path=slide_3, audio_path=audio_3, duration_seconds=13.76),
    ]

    composer = VideoComposer()
    output_mp4 = "/tmp/insertion_sort_hybrid_pilot_5pass.mp4"
    clips_dir = str(work_dir / "clips_5pass")

    print("[3/4] Thực thi render qua VideoComposer...")
    res = await composer.compose_video_with_timeline(
        scenes=scenes,
        work_dir=clips_dir,
        output_mp4_path=output_mp4,
    )

    print("\n" + "=" * 80)
    print("KẾT XUẤT THÀNH CÔNG:")
    print(f"  + Tổng thời lượng video: {res.duration_seconds:.2f}s")
    print(f"  + Thời lượng từng cảnh: {[round(d, 2) for d in res.scene_durations_seconds]}")
    print("=" * 80)

    # 4. Kiểm tra FFprobe
    meta = probe_file(output_mp4)
    format_info = meta.get("format", {})
    streams = meta.get("streams", [])
    v_stream = next((s for s in streams if s["codec_type"] == "video"), {})
    a_stream = next((s for s in streams if s["codec_type"] == "audio"), {})

    print("[4/4] Thông số FFprobe của video kết quả:")
    print(f"  * Kích thước file:  {int(format_info.get('size', 0)) / 1024:.1f} KB")
    print(f"  * Thời lượng:      {float(format_info.get('duration', 0)):.3f}s")
    print(f"  * Video Stream:    {v_stream.get('codec_name')} {v_stream.get('width')}x{v_stream.get('height')} @ {v_stream.get('r_frame_rate')} fps")
    print(f"  * Audio Stream:    {a_stream.get('codec_name')} {a_stream.get('sample_rate')} Hz, {a_stream.get('channels')} channels")

    # Lưu ra /app/media
    media_dir = Path("/app/media")
    media_dir.mkdir(parents=True, exist_ok=True)
    dest_final = media_dir / "insertion_sort_hybrid_pilot.mp4"
    shutil.copyfile(output_mp4, dest_final)
    print(f"\n[DONE] Đã lưu file kết xuất hoàn chỉnh tại: {dest_final}")


if __name__ == "__main__":
    asyncio.run(main())
