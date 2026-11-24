#!/usr/bin/env python3
"""
Manim Scene 2 (Full Trace — Hybrid Pacing) — Straight Insertion Sort
Array: [23, 78, 45, 8, 32, 56] | CO2003 — LO.3.2

Timeline (20.5s, 1280x720, 25 fps, Dark Slate #0f172a):
  - 0.0s -> 2.8s : Init array + divider after [23]
  - 2.8s -> 6.0s : Pass 1 (current=1, val=78) — detailed
  - 6.0s -> 12.2s: Pass 2 (current=2, temp=45) — detailed (supports PresentQuiz Q3)
  - 12.2s -> 15.0s: Pass 3 (current=3, temp=8) — rapid trace + walker=-1 highlight (supports Q4)
  - 15.0s -> 17.0s: Pass 4 (current=4, temp=32) — rapid trace
  - 17.0s -> 19.2s: Pass 5 (current=5, temp=56) — rapid trace -> fully sorted
  - 19.2s -> 20.5s: Hold final sorted state [8, 23, 32, 45, 56, 78]

Render command:
    manim -r 1280,720 --fps 25 -v WARNING scripts/manim_insertion_sort_scene2.py InsertionSortScene2
"""

from __future__ import annotations

import numpy as np
from manim import *

config.pixel_width = 1280
config.pixel_height = 720
config.frame_rate = 25
config.background_color = "#0f172a"


class InsertionSortScene2(Scene):
    def construct(self) -> None:
        self.camera.background_color = "#0f172a"

        BG_UNSORTED = "#1e293b"
        STROKE_UNSORTED = "#64748b"
        BG_SORTED = "#064e3b"
        STROKE_SORTED = "#22c55e"
        BG_ACTIVE = "#78350f"
        STROKE_ACTIVE = "#f59e0b"
        BG_SHIFT = "#7c2d12"
        STROKE_SHIFT = "#f97316"
        TEXT_MAIN = "#f8fafc"
        TEXT_MUTED = "#94a3b8"
        ACCENT_CYAN = "#38bdf8"

        values = [23, 78, 45, 8, 32, 56]
        n = len(values)

        box_w, box_h = 1.35, 1.15
        spacing = 1.68
        start_x = -((n - 1) * spacing) / 2.0
        array_y = -0.15
        temp_y = 1.48

        def slot_pos(idx: int) -> np.ndarray:
            return np.array([start_x + idx * spacing, array_y, 0.0])

        def divider_x(sorted_count: int) -> float:
            return (start_x + (sorted_count - 1) * spacing + start_x + sorted_count * spacing) / 2.0

        def make_cell(val: int) -> VGroup:
            rect = RoundedRectangle(
                width=box_w,
                height=box_h,
                corner_radius=0.14,
                fill_color=BG_UNSORTED,
                fill_opacity=1.0,
                stroke_color=STROKE_UNSORTED,
                stroke_width=3.0,
            )
            num = Text(str(val), font_size=36, weight=BOLD, color=TEXT_MAIN)
            num.move_to(rect.get_center())
            return VGroup(rect, num)

        def make_region_braces(sorted_count: int) -> VGroup:
            """Neo Brace theo tọa độ khe cố định để tránh lệch khung khi cell đang di chuyển."""
            base_y = array_y - box_h / 2.0
            s_line = Line(
                np.array([slot_pos(0)[0] - box_w / 2.0, base_y, 0.0]),
                np.array([slot_pos(sorted_count - 1)[0] + box_w / 2.0, base_y, 0.0]),
            )
            b_sorted = Brace(s_line, direction=DOWN, buff=0.58, color=STROKE_SORTED)
            t_sorted = Text("sorted", font_size=22, weight=BOLD, color=STROKE_SORTED)
            t_sorted.next_to(b_sorted, DOWN, buff=0.10)

            if sorted_count >= n:
                return VGroup(b_sorted, t_sorted)

            u_line = Line(
                np.array([slot_pos(sorted_count)[0] - box_w / 2.0, base_y, 0.0]),
                np.array([slot_pos(n - 1)[0] + box_w / 2.0, base_y, 0.0]),
            )
            b_unsorted = Brace(u_line, direction=DOWN, buff=0.58, color=TEXT_MUTED)
            t_unsorted = Text("unsorted", font_size=22, color=TEXT_MUTED)
            t_unsorted.next_to(b_unsorted, DOWN, buff=0.10)
            return VGroup(b_sorted, t_sorted, b_unsorted, t_unsorted)

        def make_bottom_pill(label: str, stroke_color=STROKE_UNSORTED, text_color=TEXT_MAIN) -> VGroup:
            txt = Text(label, font_size=23, weight=BOLD, color=text_color)
            pill = RoundedRectangle(
                width=max(txt.width + 0.70, 5.4),
                height=0.64,
                corner_radius=0.16,
                fill_color="#1e293b",
                fill_opacity=0.95,
                stroke_color=stroke_color,
                stroke_width=2.5,
            )
            pill.move_to(np.array([0.0, -3.22, 0.0]))
            txt.move_to(pill.get_center())
            return VGroup(pill, txt)

        def make_banner(msg: str, color=ACCENT_CYAN) -> Text:
            t = Text(msg, font_size=22, weight=BOLD, color=color)
            t.move_to(np.array([0.0, 2.66, 0.0]))
            return t

        # Tiêu đề căn trái + badge Rapid Trace góc phải (không đè nhau)
        title = Text("Straight Insertion Sort — Array Trace", font_size=30, weight=BOLD, color=TEXT_MAIN)
        title.to_edge(LEFT, buff=0.55).set_y(3.34)

        speed_badge = VGroup(
            RoundedRectangle(
                width=2.40, height=0.44, corner_radius=0.12,
                fill_color="#1e3a8a", fill_opacity=0.95,
                stroke_color=ACCENT_CYAN, stroke_width=2.0,
            ),
            Text(">> Rapid Trace", font_size=18, weight=BOLD, color=ACCENT_CYAN),
        )
        speed_badge[1].move_to(speed_badge[0].get_center())
        speed_badge.to_edge(RIGHT, buff=0.55).set_y(3.34)

        cells = [make_cell(v) for v in values]
        for i, c in enumerate(cells):
            c.move_to(slot_pos(i))

        index_labels = VGroup(*[
            Text(str(i), font_size=20, color=TEXT_MUTED).move_to(
                np.array([slot_pos(i)[0], array_y - 0.85, 0.0])
            )
            for i in range(n)
        ])

        step_banner = make_banner("Initial: first element [23] is sorted", ACCENT_CYAN)
        bottom_pill = make_bottom_pill("Array:  [23  |  78, 45, 8, 32, 56]")

        # =====================================================================
        # PHASE 1 (0.0s -> 2.8s): Khởi tạo mảng & vách ngăn sau [23]
        # =====================================================================
        self.play(
            FadeIn(title, shift=DOWN * 0.15),
            FadeIn(VGroup(*cells), lag_ratio=0.05),
            FadeIn(index_labels),
            run_time=0.8,
        )

        divider = DashedLine(
            start=np.array([divider_x(1), array_y + 0.80, 0.0]),
            end=np.array([divider_x(1), array_y - 1.05, 0.0]),
            color=STROKE_SORTED,
            stroke_width=4.0,
            dash_length=0.14,
        )
        braces = make_region_braces(1)

        self.play(
            Create(divider),
            cells[0][0].animate.set_fill(BG_SORTED).set_stroke(STROKE_SORTED),
            FadeIn(step_banner),
            FadeIn(braces),
            FadeIn(bottom_pill),
            run_time=0.8,
        )
        self.wait(1.2)  # t = 2.8s

        # =====================================================================
        # PHASE 2 (2.8s -> 6.0s): Pass 1 (current = 1, val = 78) — Chi tiết
        # =====================================================================
        b1 = make_banner("Pass 1 (current = 1): Check 78 -> 78 > 23 (keep)", STROKE_ACTIVE)
        self.play(
            ReplacementTransform(step_banner, b1),
            cells[1][0].animate.set_fill(BG_ACTIVE).set_stroke(STROKE_ACTIVE, width=4.0),
            run_time=0.7,
        )
        step_banner = b1

        cmp_arc = CurvedArrow(
            start_point=slot_pos(1) + UP * 0.65,
            end_point=slot_pos(0) + UP * 0.65,
            angle=PI / 3,
            color=STROKE_ACTIVE,
            stroke_width=3.0,
        )
        self.play(Create(cmp_arc), run_time=0.6)
        self.wait(0.5)

        braces_2 = make_region_braces(2)
        pill_2 = make_bottom_pill("After current = 1:  [23, 78  |  45, 8, 32, 56]")
        self.play(
            FadeOut(cmp_arc),
            cells[1][0].animate.set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0),
            divider.animate.set_x(divider_x(2)),
            ReplacementTransform(braces, braces_2),
            ReplacementTransform(bottom_pill, pill_2),
            run_time=0.9,
        )
        braces, bottom_pill = braces_2, pill_2
        self.wait(0.5)  # t = 6.0s

        # =====================================================================
        # PHASE 3 (6.0s -> 12.2s): Pass 2 (current = 2, temp = 45) — Chi tiết (Câu 3)
        # =====================================================================
        b2 = make_banner("Pass 2 (current = 2): Extract temp = 45", STROKE_ACTIVE)
        self.play(
            ReplacementTransform(step_banner, b2),
            cells[2][0].animate.set_fill(BG_ACTIVE).set_stroke(STROKE_ACTIVE, width=4.0),
            run_time=0.6,
        )
        step_banner = b2

        empty_slot = DashedVMobject(
            RoundedRectangle(
                width=box_w, height=box_h, corner_radius=0.14,
                stroke_color=TEXT_MUTED, stroke_width=2.2,
            ),
            num_dashes=20,
        ).move_to(slot_pos(2))

        cell_45, cell_78, cell_23 = cells[2], cells[1], cells[0]
        temp_tag = Text("temp = 45", font_size=21, weight=BOLD, color=STROKE_ACTIVE)
        temp_tag.next_to(np.array([slot_pos(2)[0], temp_y, 0.0]), RIGHT, buff=0.85)

        self.play(
            FadeIn(empty_slot),
            cell_45.animate.move_to(np.array([slot_pos(2)[0], temp_y, 0.0])),
            FadeIn(temp_tag),
            run_time=0.7,
        )

        b2_shift = make_banner("45 < 78 -> Shift 78 right to index 2", STROKE_SHIFT)
        self.play(
            ReplacementTransform(step_banner, b2_shift),
            cell_78[0].animate.set_fill(BG_SHIFT).set_stroke(STROKE_SHIFT, width=4.0),
            run_time=0.6,
        )
        step_banner = b2_shift

        self.play(
            cell_78.animate.move_to(slot_pos(2)),
            empty_slot.animate.move_to(slot_pos(1)),
            run_time=0.8,
        )

        b2_ins = make_banner("45 > 23 -> Insert 45 at index 1", STROKE_SORTED)
        self.play(
            ReplacementTransform(step_banner, b2_ins),
            Indicate(cell_23, color=STROKE_SORTED, scale_factor=1.08),
            run_time=0.7,
        )
        step_banner = b2_ins

        self.play(
            cell_45.animate.move_to(np.array([slot_pos(1)[0], temp_y, 0.0])),
            temp_tag.animate.next_to(np.array([slot_pos(1)[0], temp_y, 0.0]), RIGHT, buff=0.85),
            run_time=0.4,
        )
        self.play(
            cell_45.animate.move_to(slot_pos(1)),
            FadeOut(empty_slot),
            FadeOut(temp_tag),
            run_time=0.5,
        )

        cells[1], cells[2] = cell_45, cell_78
        braces_3 = make_region_braces(3)
        pill_3 = make_bottom_pill(
            "After current = 2:  [23, 45, 78  |  8, 32, 56]",
            stroke_color=STROKE_SORTED,
            text_color="#bbf7d0",
        )
        self.play(
            cell_45[0].animate.set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0),
            cell_78[0].animate.set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0),
            divider.animate.set_x(divider_x(3)),
            ReplacementTransform(braces, braces_3),
            ReplacementTransform(bottom_pill, pill_3),
            run_time=0.8,
        )
        braces, bottom_pill = braces_3, pill_3
        self.wait(1.1)  # t = 12.2s — dừng đủ lâu cho trạng thái Câu 3

        # =====================================================================
        # PHASE 4 (12.2s -> 15.0s): Pass 3 (temp = 8) — Rapid Trace (Câu 4: walker = -1)
        # =====================================================================
        b3 = make_banner("Pass 3 (temp = 8): Shift 3 elements -> walker = -1, insert [0]", ACCENT_CYAN)
        cell_8 = cells[3]
        cell_8[0].set_fill(BG_ACTIVE).set_stroke(STROKE_ACTIVE, width=4.0)
        self.play(
            FadeIn(speed_badge),
            ReplacementTransform(step_banner, b3),
            cell_8.animate.move_to(np.array([slot_pos(3)[0], temp_y, 0.0])),
            run_time=0.6,
        )
        step_banner = b3

        self.play(
            cells[2].animate.move_to(slot_pos(3)),
            cells[1].animate.move_to(slot_pos(2)),
            cells[0].animate.move_to(slot_pos(1)),
            cell_8.animate.move_to(np.array([slot_pos(0)[0], temp_y, 0.0])),
            run_time=0.8,
        )

        cells = [cell_8, cells[0], cells[1], cells[2], cells[4], cells[5]]
        braces_4 = make_region_braces(4)
        pill_4 = make_bottom_pill("After current = 3:  [8, 23, 45, 78  |  32, 56]")
        cell_8[0].set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0)
        self.play(
            cell_8.animate.move_to(slot_pos(0)),
            divider.animate.set_x(divider_x(4)),
            ReplacementTransform(braces, braces_4),
            ReplacementTransform(bottom_pill, pill_4),
            run_time=0.8,
        )
        braces, bottom_pill = braces_4, pill_4
        self.wait(0.6)  # t = 15.0s

        # =====================================================================
        # PHASE 5 (15.0s -> 17.0s): Pass 4 (temp = 32) — Rapid Trace
        # =====================================================================
        b4 = make_banner("Pass 4 (temp = 32): Shift [45, 78] right -> insert [2]", ACCENT_CYAN)
        cell_32 = cells[4]
        cell_32[0].set_fill(BG_ACTIVE).set_stroke(STROKE_ACTIVE, width=4.0)
        self.play(
            ReplacementTransform(step_banner, b4),
            cell_32.animate.move_to(np.array([slot_pos(4)[0], temp_y, 0.0])),
            run_time=0.5,
        )
        step_banner = b4

        self.play(
            cells[3].animate.move_to(slot_pos(4)),
            cells[2].animate.move_to(slot_pos(3)),
            cell_32.animate.move_to(np.array([slot_pos(2)[0], temp_y, 0.0])),
            run_time=0.6,
        )

        cells = [cells[0], cells[1], cell_32, cells[2], cells[3], cells[5]]
        braces_5 = make_region_braces(5)
        pill_5 = make_bottom_pill("After current = 4:  [8, 23, 32, 45, 78  |  56]")
        cell_32[0].set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0)
        self.play(
            cell_32.animate.move_to(slot_pos(2)),
            divider.animate.set_x(divider_x(5)),
            ReplacementTransform(braces, braces_5),
            ReplacementTransform(bottom_pill, pill_5),
            run_time=0.6,
        )
        braces, bottom_pill = braces_5, pill_5
        self.wait(0.3)  # t = 17.0s

        # =====================================================================
        # PHASE 6 (17.0s -> 20.5s): Pass 5 (temp = 56) -> Hoàn tất sắp xếp
        # =====================================================================
        b5 = make_banner("Pass 5 (temp = 56): Shift [78] right -> insert [4]", ACCENT_CYAN)
        cell_56 = cells[5]
        cell_56[0].set_fill(BG_ACTIVE).set_stroke(STROKE_ACTIVE, width=4.0)
        self.play(
            ReplacementTransform(step_banner, b5),
            cell_56.animate.move_to(np.array([slot_pos(5)[0], temp_y, 0.0])),
            run_time=0.5,
        )
        step_banner = b5

        self.play(
            cells[4].animate.move_to(slot_pos(5)),
            cell_56.animate.move_to(np.array([slot_pos(4)[0], temp_y, 0.0])),
            run_time=0.5,
        )

        cells = [cells[0], cells[1], cells[2], cells[3], cell_56, cells[4]]
        braces_all = make_region_braces(6)
        b_done = make_banner("Sorted Complete! All 6 elements in ascending order", STROKE_SORTED)
        pill_done = make_bottom_pill(
            "Sorted:  [8, 23, 32, 45, 56, 78]",
            stroke_color=STROKE_SORTED,
            text_color="#bbf7d0",
        )

        cell_56[0].set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0)
        self.play(
            cell_56.animate.move_to(slot_pos(4)),
            FadeOut(divider),
            FadeOut(speed_badge),
            ReplacementTransform(step_banner, b_done),
            ReplacementTransform(braces, braces_all),
            ReplacementTransform(bottom_pill, pill_done),
            run_time=0.8,
        )
        self.play(
            *[Indicate(c, color=STROKE_SORTED, scale_factor=1.05) for c in cells],
            run_time=0.4,
        )
        self.wait(1.3)  # t = 20.5s
