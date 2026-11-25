from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f172a"
        BG_DEFAULT = "#1e293b"
        STROKE_DEFAULT = "#64748b"
        BG_LEFT = "#1e3a5f"
        STROKE_LEFT = "#38bdf8"
        BG_RIGHT = "#4c1d95"
        STROKE_RIGHT = "#a78bfa"
        BG_SORTED = "#064e3b"
        STROKE_SORTED = "#10b981"
        TEXT_WHITE = "#f8fafc"

        values = [38, 27, 43, 3, 9, 82]
        n = len(values)
        box_w = min(1.05, 9.2 / max(n, 1))
        box_h = 0.85
        gap = 0.22

        def make_array_row(vals, y_pos, fill_c=BG_DEFAULT, stroke_c=STROKE_DEFAULT, x_center=0.0):
            grp = VGroup()
            step = box_w + gap
            sx = x_center - ((len(vals) - 1) * step) / 2.0
            for i, v in enumerate(vals):
                rect = RoundedRectangle(
                    width=box_w, height=box_h, corner_radius=0.12,
                    fill_color=fill_c, fill_opacity=1.0,
                    stroke_color=stroke_c, stroke_width=2.5,
                )
                txt = Text(str(v), font_size=26, weight=BOLD, color=TEXT_WHITE)
                cell = VGroup(rect, txt).move_to(np.array([sx + i * step, y_pos, 0.0]))
                grp.add(cell)
            return grp

        title = Text('Merge Sort — Divide & Conquer Trace', font_size=32, weight=BOLD, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.35)
        if title.width > 12.0:
            title.scale_to_fit_width(12.0)

        banner = Text(f"Input array (n = {n}): {values}", font_size=24, color=STROKE_LEFT)
        banner.next_to(title, DOWN, buff=0.25)

        root_row = make_array_row(values, y_pos=1.25)
        self.play(FadeIn(title), FadeIn(banner), FadeIn(root_row), run_time=1.0)
        self.wait(0.8)

        # Phase 1: Divide into Left & Right halves
        mid = n // 2
        left_vals = values[:mid]
        right_vals = values[mid:]
        b_div = Text(f"Divide: Left {left_vals}  |  Right {right_vals}", font_size=23, color="#f59e0b")
        b_div.next_to(title, DOWN, buff=0.25)

        left_row = make_array_row(left_vals, y_pos=-0.1, fill_c=BG_LEFT, stroke_c=STROKE_LEFT, x_center=-3.1)
        right_row = make_array_row(right_vals, y_pos=-0.1, fill_c=BG_RIGHT, stroke_c=STROKE_RIGHT, x_center=3.1)
        arr_l = Arrow(root_row.get_bottom() + LEFT * 0.5, left_row.get_top(), color=STROKE_LEFT, buff=0.15)
        arr_r = Arrow(root_row.get_bottom() + RIGHT * 0.5, right_row.get_top(), color=STROKE_RIGHT, buff=0.15)

        self.play(
            ReplacementTransform(banner, b_div),
            GrowArrow(arr_l), GrowArrow(arr_r),
            FadeIn(left_row), FadeIn(right_row),
            run_time=1.3,
        )
        banner = b_div
        self.wait(0.9)

        # Phase 2: Sort each half recursively
        left_sorted = sorted(left_vals)
        right_sorted = sorted(right_vals)
        b_sub = Text(f"Conquer (Recursive Sort): {left_sorted}  &  {right_sorted}", font_size=23, color=STROKE_LEFT)
        b_sub.next_to(title, DOWN, buff=0.25)

        left_s_row = make_array_row(left_sorted, y_pos=-0.1, fill_c=BG_LEFT, stroke_c=STROKE_LEFT, x_center=-3.1)
        right_s_row = make_array_row(right_sorted, y_pos=-0.1, fill_c=BG_RIGHT, stroke_c=STROKE_RIGHT, x_center=3.1)

        self.play(
            ReplacementTransform(banner, b_sub),
            ReplacementTransform(left_row, left_s_row),
            ReplacementTransform(right_row, right_s_row),
            run_time=1.2,
        )
        banner = b_sub
        self.wait(0.9)

        # Phase 3: Merge two sorted halves element-by-element
        merged_vals = sorted(values)
        b_merge = Text("Merge: Compare front elements & place smaller value", font_size=23, color=STROKE_SORTED)
        b_merge.next_to(title, DOWN, buff=0.25)
        self.play(ReplacementTransform(banner, b_merge), run_time=0.6)
        banner = b_merge

        merged_row = make_array_row(merged_vals, y_pos=-1.9, fill_c=BG_SORTED, stroke_c=STROKE_SORTED, x_center=0.0)
        merge_arr_l = Arrow(left_s_row.get_bottom(), merged_row.get_top() + LEFT * 0.6, color=STROKE_SORTED, buff=0.15)
        merge_arr_r = Arrow(right_s_row.get_bottom(), merged_row.get_top() + RIGHT * 0.6, color=STROKE_SORTED, buff=0.15)
        self.play(GrowArrow(merge_arr_l), GrowArrow(merge_arr_r), run_time=0.6)

        for cell in merged_row:
            self.play(FadeIn(cell, shift=DOWN * 0.25), run_time=0.45)

        b_done = Text(f"Merge Complete — O(n log n): {merged_vals}", font_size=25, weight=BOLD, color=STROKE_SORTED)
        b_done.next_to(title, DOWN, buff=0.25)
        self.play(ReplacementTransform(banner, b_done), run_time=0.5)
        self.play(*[Indicate(c, color=STROKE_SORTED, scale_factor=1.06) for c in merged_row], run_time=0.6)
        self.wait(1.5)
