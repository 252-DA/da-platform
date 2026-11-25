"""Script kiểm thử nhanh ManimGenerator (Tầng 1: Merge Sort Template)."""
import asyncio
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worker"))

# Stub nhẹ document_chunk.shared khi chạy độc lập ngoài container
m = types.ModuleType("document_chunk")
m_s = types.ModuleType("document_chunk.shared")
m_l = types.ModuleType("document_chunk.shared.logger")
m_r = types.ModuleType("document_chunk.shared.result")


class _Logger:
    def info(self, *a, **k):
        print("INFO", a, k, flush=True)

    def warning(self, *a, **k):
        print("WARN", a, k, flush=True)

    def error(self, *a, **k):
        print("ERR", a, k, flush=True)


m_l.get_logger = lambda name: _Logger()
m_r.Result = object
sys.modules["document_chunk"] = m
sys.modules["document_chunk.shared"] = m_s
sys.modules["document_chunk.shared.logger"] = m_l
sys.modules["document_chunk.shared.result"] = m_r

from worker.services.manim_generator import ManimGenerationRequest, ManimGenerator  # noqa: E402


async def main() -> None:
    print("Starting Merge Sort template render...", flush=True)
    gen = ManimGenerator()
    req = ManimGenerationRequest(
        title="Merge Sort — Divide & Conquer",
        narration="Minh hoa Merge Sort tren mang 6 phan tu",
        visual_mode="MANIM_TEMPLATE",
        template_name="merge_sort",
        template_params={"array": [38, 27, 43, 3, 9, 82]},
        timeout_seconds=120,
    )
    out = str(Path(__file__).resolve().parents[1] / "media" / "test_merge_sort_template.mp4")
    res = await gen.generate_scene_clip(req, out)
    print(
        f"RESULT: success={res.success} tier={res.tier_used} attempts={res.attempts} "
        f"err_cat={res.error_category} err={res.error} clip={res.clip_path}",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
