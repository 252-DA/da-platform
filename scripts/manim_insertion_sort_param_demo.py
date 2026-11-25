from manim import *
import numpy as np


class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f172a"
        BG_DEFAULT = "#1e293b"
        STROKE_DEFAULT = "#64748b"
        BG_SORTED = "#064e3b"
        STROKE_SORTED = "#10b981"
        BG_ACTIVE = "#78350f"
        STROKE_ACTIVE = "#f59e0b"
        TEXT_WHITE = "#f8fafc"
        TEXT_MUTED = "#94a3b8"

        values = [15, 42, 7, 29, 11]
        n = len(values)
        box_w = min(1.2, 9.0 / max(n, 1))
        box_h = box_w
        gap = 0.28
        step_x = box_w + gap
        start_x = -((n - 1) * step_x) / 2.0
        base_y = -0.35
        temp_y = base_y + box_h + 0.65

        def slot_pos(idx: int) -> np.ndarray:
            return np.array([start_x + idx * step_x, base_y, 0.0])

        title = Text('Insertion Sort — Parameterized [15, 42, 7, 29, 11]', font_size=32, weight=BOLD, color=TEXT_WHITE)
        title.to_edge(UP, buff=0.4)
        if title.width > 12.0:
            title.scale_to_fit_width(12.0)

        banner = Text(f"Initial array: {values}", font_size=24, color="#38bdf8")
        banner.next_to(title, DOWN, buff=0.3)

        cells = []
        idx_labels = VGroup()
        for i, v in enumerate(values):
            rect = RoundedRectangle(
                width=box_w, height=box_h, corner_radius=0.14,
                fill_color=BG_DEFAULT, fill_opacity=1.0,
                stroke_color=STROKE_DEFAULT, stroke_width=2.5,
            )
            num = Text(str(v), font_size=30, weight=BOLD, color=TEXT_WHITE)
            cell = VGroup(rect, num).move_to(slot_pos(i))
            cells.append(cell)
            lbl = Text(str(i), font_size=18, color=TEXT_MUTED)
            lbl.next_to(slot_pos(i), DOWN, buff=box_h / 2 + 0.22)
            idx_labels.add(lbl)

        self.play(FadeIn(title), FadeIn(banner), FadeIn(VGroup(*cells)), FadeIn(idx_labels), run_time=0.9)
        cells[0][0].set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0)
        self.wait(0.6)

        arr_state = list(values)
        for current in range(1, n):
            key_val = arr_state[current]
            key_cell = cells[current]
            b_pick = Text(f"Pass {current}: Extract temp = {key_val}", font_size=24, color=STROKE_ACTIVE)
            b_pick.next_to(title, DOWN, buff=0.3)

            key_cell[0].set_fill(BG_ACTIVE).set_stroke(STROKE_ACTIVE, width=4.0)
            self.play(
                ReplacementTransform(banner, b_pick),
                key_cell.animate.move_to(np.array([slot_pos(current)[0], temp_y, 0.0])),
                run_time=0.55,
            )
            banner = b_pick

            walker = current - 1
            shifts = []
            while walker >= 0 and arr_state[walker] > key_val:
                arr_state[walker + 1] = arr_state[walker]
                cells[walker + 1] = cells[walker]
                shifts.append(cells[walker].animate.move_to(slot_pos(walker + 1)))
                walker -= 1

            target_idx = walker + 1
            arr_state[target_idx] = key_val
            cells[target_idx] = key_cell

            if shifts:
                shifts.append(key_cell.animate.move_to(np.array([slot_pos(target_idx)[0], temp_y, 0.0])))
                self.play(*shifts, run_time=0.65)

            b_ins = Text(f"Insert {key_val} at index [{target_idx}] -> {arr_state}", font_size=22, color=STROKE_SORTED)
            b_ins.next_to(title, DOWN, buff=0.3)
            if b_ins.width > 12.0:
                b_ins.scale_to_fit_width(12.0)

            key_cell[0].set_fill(BG_SORTED).set_stroke(STROKE_SORTED, width=3.0)
            self.play(
                ReplacementTransform(banner, b_ins),
                key_cell.animate.move_to(slot_pos(target_idx)),
                run_time=0.6,
            )
            banner = b_ins
            self.wait(0.35)

        b_done = Text(f"Sorted Complete: {arr_state}", font_size=26, weight=BOLD, color=STROKE_SORTED)
        b_done.next_to(title, DOWN, buff=0.3)
        self.play(ReplacementTransform(banner, b_done), run_time=0.5)
        self.play(*[Indicate(c, color=STROKE_SORTED, scale_factor=1.06) for c in cells], run_time=0.5)
        self.wait(1.2)
