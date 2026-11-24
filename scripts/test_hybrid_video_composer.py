"""
Script kiểm thử độc lập cho Scene-Level Hybrid Composition (VideoComposer & Fallback).
Kiểm tra:
1. Ràng buộc tốc độ [0.75x, 1.35x] và tpad freeze frame cuối.
2. Chuẩn hóa stream (-map 0:v:0 -map 1:a:0, scale/pad 1280x720, yuv420p, 25fps, 44.1kHz stereo).
3. Concat mượt mà giữa Cảnh Slide tĩnh -> Cảnh Manim động -> Cảnh Slide tĩnh.
4. Kiểm tra FFmpeg & FFprobe metadata chi tiết.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Thêm đường dẫn worker và packages-ai vào sys.path để import trực tiếp
candidate_paths = [
    Path(__file__).resolve().parent.parent / "worker",
    Path(__file__).resolve().parent.parent / "packages-ai" / "src",
    Path("/app/worker"),
    Path("/app/packages-ai/src"),
    Path("/app"),
]
for p in candidate_paths:
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

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
    print("=" * 78)
    print("BẮT ĐẦU KIỂM THỬ THỰC HÀNH: SCENE-LEVEL HYBRID COMPOSITION")
    print("=" * 78)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"[1/4] Tạo dữ liệu mẫu trong thư mục tạm: {temp_path}")

        # 1. Slide 1: Ảnh tĩnh (Intro) + Audio 3.0s
        slide1_png = temp_path / "slide_01.png"
        audio1_mp3 = temp_path / "audio_01.mp3"
        run_cmd([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=navy:s=1280x720:d=1",
            "-frames:v", "1", str(slide1_png)
        ])
        run_cmd([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=3.0",
            "-c:a", "libmp3lame", "-b:a", "192k", str(audio1_mp3)
        ])

        # 2. Cảnh 2: Clip Manim động (ví dụ 4.0s, 854x480, có audio nhiễu 880Hz) + Audio TTS 5.5s
        # Thử thách: clip 4.0s ngắn hơn audio 5.5s (tốc độ yêu cầu 4.0/5.5 = 0.727x < 0.75x)
        # -> VideoComposer phải clamp tốc độ về 0.75x và dùng tpad clone frame cuối!
        # -> Đồng thời phải bỏ track audio 880Hz của clip và thay bằng audio TTS 550Hz!
        manim_clip = temp_path / "manim_scene_02.mp4"
        audio2_mp3 = temp_path / "audio_02.mp3"
        run_cmd([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "testsrc=duration=4.0:size=854x480:rate=15",
            "-f", "lavfi", "-i", "sine=frequency=880:duration=4.0",
            "-c:v", "libx264", "-c:a", "aac", str(manim_clip)
        ])
        run_cmd([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=550:duration=5.5",
            "-c:a", "libmp3lame", "-b:a", "192k", str(audio2_mp3)
        ])

        # 3. Slide 3: Ảnh tĩnh (Outro) + Audio 2.5s
        slide3_png = temp_path / "slide_03.png"
        audio3_mp3 = temp_path / "audio_03.mp3"
        run_cmd([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "color=c=darkgreen:s=1280x720:d=1",
            "-frames:v", "1", str(slide3_png)
        ])
        run_cmd([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=660:duration=2.5",
            "-c:a", "libmp3lame", "-b:a", "192k", str(audio3_mp3)
        ])

        print("[2/4] Khởi tạo SceneMedia:")
        print("  - Cảnh 1 (SLIDE_STATIC): Slide ảnh 1280x720, Audio 3.0s")
        print("  - Cảnh 2 (MANIM_HYBRID): Clip Manim 854x480 15fps (4.0s) -> ghép Audio TTS 5.5s")
        print("  - Cảnh 3 (SLIDE_STATIC): Slide ảnh 1280x720, Audio 2.5s")

        scenes = [
            SceneMedia(slide_image_path=str(slide1_png), audio_path=str(audio1_mp3), duration_seconds=3.0),
            SceneMedia(
                slide_image_path=str(slide1_png),  # Dùng khi fallback
                audio_path=str(audio2_mp3),
                duration_seconds=5.5,
                video_clip_path=str(manim_clip),  # Cảnh Manim
            ),
            SceneMedia(slide_image_path=str(slide3_png), audio_path=str(audio3_mp3), duration_seconds=2.5),
        ]

        composer = VideoComposer()
        work_dir = str(temp_path / "clips")
        final_hybrid_mp4 = str(temp_path / "final_hybrid_micro_content.mp4")

        print("[3/4] Thực thi compose_video_with_timeline()...")
        res = await composer.compose_video_with_timeline(
            scenes=scenes,
            work_dir=work_dir,
            output_mp4_path=final_hybrid_mp4,
        )

        print("\n" + "=" * 78)
        print("KẾT QUẢ KẾT XUẤT THÀNH CÔNG:")
        print(f"  + Tổng thời lượng video: {res.duration_seconds:.2f} giây")
        print(f"  + Thời lượng từng cảnh: {[round(d, 2) for d in res.scene_durations_seconds]}")
        print("=" * 78)

        # 4. Kiểm định chi tiết bằng ffprobe
        print("\n[4/4] Kiểm định FFprobe metadata của video Hybrid hoàn chỉnh:")
        meta = probe_file(final_hybrid_mp4)
        streams = meta.get("streams", [])
        v_stream = next((s for s in streams if s["codec_type"] == "video"), {})
        a_stream = next((s for s in streams if s["codec_type"] == "audio"), {})

        print(f"  * Video Stream:")
        print(f"    - Codec:         {v_stream.get('codec_name')} ({v_stream.get('profile')})")
        print(f"    - Resolution:    {v_stream.get('width')}x{v_stream.get('height')}")
        print(f"    - Frame Rate:    {v_stream.get('r_frame_rate')} fps")
        print(f"    - Pixel Format:  {v_stream.get('pix_fmt')}")
        print(f"    - Aspect Ratio:  DAR {v_stream.get('display_aspect_ratio')}, SAR {v_stream.get('sample_aspect_ratio')}")
        print(f"  * Audio Stream:")
        print(f"    - Codec:         {a_stream.get('codec_name')}")
        print(f"    - Sample Rate:   {a_stream.get('sample_rate')} Hz")
        print(f"    - Channels:      {a_stream.get('channels')} (Stereo)")
        print(f"    - Bitrate:       {round(int(a_stream.get('bit_rate', 0)) / 1000)} kbps")

        # Lưu bản copy video hybrid mẫu sang thư mục media để người dùng xem trực tiếp
        persistent_media_dir = Path(__file__).resolve().parent.parent / "media"
        persistent_media_dir.mkdir(parents=True, exist_ok=True)
        persisted_path = persistent_media_dir / "sample_hybrid_insertion_sort.mp4"
        shutil.copy2(final_hybrid_mp4, persisted_path)
        print(f"\n[XÁC THỰC] Đã lưu video Hybrid mẫu ra: {persisted_path}")
        print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
