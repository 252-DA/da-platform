"""
Manim Full Case Study: Complete QuickSort Partition Algorithm (PASS 1 & Recursion)
Based on Kruse & Ryba lecture slides (Slides 3-30)

Demonstrates solving the critical limitation of 26 static lecture slides
by animating the entire Partition pass and recursive resolution in a single coherent video.
"""

from manim import *
import numpy as np

class QuickSortFullScene(Scene):
    def construct(self):
        # ── 1. Header & Setup ──
        title = Text("QuickSort: Complete Partition (Kruse & Ryba)", font_size=32, color=BLUE)
        title.to_edge(UP, buff=0.4)
        self.play(Write(title))

        # Initial array from Slide 3
        # 60 20 10 80 40 50 7 30 100
        # Pivot 40 is selected, swapped with first element -> [40, 20, 10, 80, 60, 50, 7, 30, 100]
        raw_vals = [40, 20, 10, 80, 60, 50, 7, 30, 100]
        n = len(raw_vals)

        box_width = 0.95
        start_x = -3.8

        boxes = []
        labels = []
        indices = []

        for i, val in enumerate(raw_vals):
            pos = np.array([start_x + i * (box_width + 0.05), 0.8, 0])
            box = Square(side_length=box_width)
            box.set_stroke(WHITE, 1.5)
            if i == 0:
                box.set_fill(RED, opacity=0.85)
            else:
                box.set_fill(GRAY_D, opacity=0.5)
            box.move_to(pos)
            boxes.append(box)

            lbl = Text(str(val), font_size=24, color=WHITE if i != 0 else YELLOW)
            lbl.move_to(pos)
            labels.append(lbl)

            idx_lbl = Text(f"[{i}]", font_size=16, color=GRAY_B)
            idx_lbl.next_to(box, DOWN, buff=0.15)
            indices.append(idx_lbl)

        boxes_vg = VGroup(*boxes)
        labels_vg = VGroup(*labels)
        indices_vg = VGroup(*indices)

        self.play(Create(boxes_vg), Write(labels_vg), Write(indices_vg), run_time=1.5)

        # Pivot callout
        pivot_tag = Text("pivot = 40 (index 0)", font_size=20, color=RED)
        pivot_tag.next_to(boxes[0], UP, buff=0.35)
        self.play(FadeIn(pivot_tag))

        # Pointers: too_big_index (starts at 1), too_small_index (starts at 8)
        ptr_big = Arrow(start=DOWN * 0.7, end=UP * 0.05, color=YELLOW, buff=0)
        ptr_big.next_to(indices[1], DOWN, buff=0.1)
        lbl_big = Text("too_big", font_size=15, color=YELLOW)
        lbl_big.next_to(ptr_big, DOWN, buff=0.08)
        big_group = VGroup(ptr_big, lbl_big)

        ptr_small = Arrow(start=DOWN * 0.7, end=UP * 0.05, color=GREEN, buff=0)
        ptr_small.next_to(indices[8], DOWN, buff=0.1)
        lbl_small = Text("too_small", font_size=15, color=GREEN)
        lbl_small.next_to(ptr_small, DOWN, buff=0.08)
        small_group = VGroup(ptr_small, lbl_small)

        self.play(FadeIn(big_group), FadeIn(small_group))

        step_text = Text(
            "Slide 4-5: Initialize too_big_index = [1], too_small_index = [8]",
            font_size=18, color=WHITE
        )
        step_text.to_edge(DOWN, buff=0.5)
        self.play(Write(step_text))
        self.wait(1)

        # Track array values & label references
        curr_vals = list(raw_vals)
        curr_lbls = list(labels)

        # ══════════════════════════════════════════════════
        # ROUND 1 (Slides 5 - 11): Swap 80 and 30
        # ══════════════════════════════════════════════════
        # 1. Advance too_big_index: 20 <= 40, 10 <= 40 -> stops at 80 > 40 (index 3)
        self.play(step_text.animate.become(
            Text("Round 1: Advance too_big_index until data[i] > 40 -> stops at [3] (80)", font_size=17, color=YELLOW).to_edge(DOWN, buff=0.5)
        ))
        self.play(big_group.animate.next_to(indices[3], DOWN, buff=0.1), run_time=1.2)
        boxes[3].set_fill(YELLOW, opacity=0.45)
        self.wait(0.6)

        # 2. Retreat too_small_index: 100 > 40 -> stops at 30 <= 40 (index 7)
        self.play(step_text.animate.become(
            Text("Round 1: Retreat too_small_index until data[j] <= 40 -> stops at [7] (30)", font_size=17, color=GREEN).to_edge(DOWN, buff=0.5)
        ))
        self.play(small_group.animate.next_to(indices[7], DOWN, buff=0.1), run_time=1.0)
        boxes[7].set_fill(GREEN, opacity=0.45)
        self.wait(0.6)

        # 3. Swap data[3] and data[7] (Slides 10-11)
        self.play(step_text.animate.become(
            Text("Round 1 Swap: data[3] (80) and data[7] (30) [too_big < too_small]", font_size=17, color=ORANGE).to_edge(DOWN, buff=0.5)
        ))
        swap_arc1 = CurvedArrow(boxes[3].get_top() + UP*0.1, boxes[7].get_top() + UP*0.1, radius=-4, color=ORANGE)
        self.play(Create(swap_arc1))

        pos_3 = curr_lbls[3].get_center()
        pos_7 = curr_lbls[7].get_center()
        self.play(
            curr_lbls[3].animate.move_to(pos_7),
            curr_lbls[7].animate.move_to(pos_3),
            run_time=1.2
        )
        self.play(FadeOut(swap_arc1))
        # Update references & reset box highlight
        curr_vals[3], curr_vals[7] = curr_vals[7], curr_vals[3]
        curr_lbls[3], curr_lbls[7] = curr_lbls[7], curr_lbls[3]
        boxes[3].set_fill(GRAY_D, opacity=0.5)
        boxes[7].set_fill(GRAY_D, opacity=0.5)
        self.wait(0.8)

        # ══════════════════════════════════════════════════
        # ROUND 2 (Slides 12 - 18): Swap 60 and 7
        # ══════════════════════════════════════════════════
        # Advance too_big: data[3]=30 <= 40 -> stops at data[4]=60 > 40 (index 4)
        self.play(step_text.animate.become(
            Text("Round 2: Advance too_big_index -> data[3]=30 <= 40, stops at [4] (60 > 40)", font_size=17, color=YELLOW).to_edge(DOWN, buff=0.5)
        ))
        self.play(big_group.animate.next_to(indices[4], DOWN, buff=0.1), run_time=1.0)
        boxes[4].set_fill(YELLOW, opacity=0.45)
        self.wait(0.6)

        # Retreat too_small: data[7]=80 > 40 -> stops at data[6]=7 <= 40 (index 6)
        self.play(step_text.animate.become(
            Text("Round 2: Retreat too_small_index -> data[7]=80 > 40, stops at [6] (7 <= 40)", font_size=17, color=GREEN).to_edge(DOWN, buff=0.5)
        ))
        self.play(small_group.animate.next_to(indices[6], DOWN, buff=0.1), run_time=1.0)
        boxes[6].set_fill(GREEN, opacity=0.45)
        self.wait(0.6)

        # Swap data[4] (60) and data[6] (7) (Slides 17-18)
        self.play(step_text.animate.become(
            Text("Round 2 Swap: data[4] (60) and data[6] (7) [too_big < too_small]", font_size=17, color=ORANGE).to_edge(DOWN, buff=0.5)
        ))
        swap_arc2 = CurvedArrow(boxes[4].get_top() + UP*0.1, boxes[6].get_top() + UP*0.1, radius=-3, color=ORANGE)
        self.play(Create(swap_arc2))

        pos_4 = curr_lbls[4].get_center()
        pos_6 = curr_lbls[6].get_center()
        self.play(
            curr_lbls[4].animate.move_to(pos_6),
            curr_lbls[6].animate.move_to(pos_4),
            run_time=1.2
        )
        self.play(FadeOut(swap_arc2))
        curr_vals[4], curr_vals[6] = curr_vals[6], curr_vals[4]
        curr_lbls[4], curr_lbls[6] = curr_lbls[6], curr_lbls[4]
        boxes[4].set_fill(GRAY_D, opacity=0.5)
        boxes[6].set_fill(GRAY_D, opacity=0.5)
        self.wait(0.8)

        # ══════════════════════════════════════════════════
        # ROUND 3 (Slides 19 - 26): Pointers Cross!
        # ══════════════════════════════════════════════════
        # Advance too_big: data[4]=7 <= 40 -> stops at data[5]=50 > 40 (index 5)
        self.play(step_text.animate.become(
            Text("Round 3: Advance too_big_index -> data[4]=7 <= 40, stops at [5] (50 > 40)", font_size=17, color=YELLOW).to_edge(DOWN, buff=0.5)
        ))
        self.play(big_group.animate.next_to(indices[5], DOWN, buff=0.1), run_time=1.0)
        boxes[5].set_fill(YELLOW, opacity=0.45)
        self.wait(0.6)

        # Retreat too_small: data[6]=60 > 40, data[5]=50 > 40 -> stops at data[4]=7 <= 40 (index 4)
        self.play(step_text.animate.become(
            Text("Round 3: Retreat too_small_index -> stops at [4] (7 <= 40). Pointers cross!", font_size=17, color=RED_B).to_edge(DOWN, buff=0.5)
        ))
        self.play(small_group.animate.next_to(indices[4], DOWN, buff=0.1), run_time=1.2)
        boxes[4].set_fill(GREEN, opacity=0.45)
        self.wait(0.8)

        # Pointers have crossed: too_small (4) < too_big (5) -> No swap! (Slide 25-26)
        cross_alert = Text("too_small_index (4) <= too_big_index (5) -> Partition loop terminates!", font_size=18, color=RED)
        cross_alert.next_to(step_text, UP, buff=0.25)
        self.play(Write(cross_alert))
        self.wait(1.5)

        # ══════════════════════════════════════════════════
        # FINAL PIVOT PLACEMENT (Slides 27 - 28)
        # ══════════════════════════════════════════════════
        self.play(
            FadeOut(cross_alert),
            step_text.animate.become(
                Text("Final Step: Swap pivot data[0] (40) with data[too_small] (7 at index [4])", font_size=17, color=GOLD).to_edge(DOWN, buff=0.5)
            )
        )
        boxes[5].set_fill(GRAY_D, opacity=0.5)
        boxes[4].set_fill(GRAY_D, opacity=0.5)

        pivot_arc = CurvedArrow(boxes[0].get_top() + UP*0.15, boxes[4].get_top() + UP*0.15, radius=-4, color=GOLD)
        self.play(Create(pivot_arc))

        pos_0 = curr_lbls[0].get_center()
        pos_4 = curr_lbls[4].get_center()

        self.play(
            curr_lbls[0].animate.move_to(pos_4),
            curr_lbls[4].animate.move_to(pos_0),
            boxes[0].animate.set_fill(GRAY_D, opacity=0.5),
            boxes[4].animate.set_fill(GOLD, opacity=0.9),
            run_time=1.5
        )
        self.play(FadeOut(pivot_arc))

        curr_vals[0], curr_vals[4] = curr_vals[4], curr_vals[0]
        curr_lbls[0], curr_lbls[4] = curr_lbls[4], curr_lbls[0]

        # Update pivot tag to index 4
        self.play(
            pivot_tag.animate.become(
                Text("pivot = 40 (sorted position [4])", font_size=19, color=GOLD).next_to(boxes[4], UP, buff=0.35)
            ),
            FadeOut(big_group),
            FadeOut(small_group)
        )
        self.wait(1)

        # ══════════════════════════════════════════════════
        # RESULT OF PASS 1 (Slides 29 - 30)
        # ══════════════════════════════════════════════════
        # Subarray Left: [0..3] = [7, 20, 10, 30] <= 40
        left_brace = Brace(boxes_vg[0:4], DOWN, buff=0.15)
        left_text = Text("Left: <= 40", font_size=16, color=BLUE_C)
        left_text.next_to(left_brace, DOWN, buff=0.1)

        # Subarray Right: [5..8] = [50, 60, 80, 100] > 40
        right_brace = Brace(boxes_vg[5:9], DOWN, buff=0.15)
        right_text = Text("Right: > 40", font_size=16, color=GREEN_C)
        right_text.next_to(right_brace, DOWN, buff=0.1)

        self.play(
            GrowFromCenter(left_brace), Write(left_text),
            GrowFromCenter(right_brace), Write(right_text),
            step_text.animate.become(
                Text("Result of PASS 1: Complete Partition achieved (replaces 26 static slides!)", font_size=18, color=GREEN).to_edge(DOWN, buff=0.3)
            )
        )
        self.wait(2)

        # ══════════════════════════════════════════════════
        # RECURSIVE COMPLETION (Slide 30): Final sorted array
        # ══════════════════════════════════════════════════
        self.play(
            FadeOut(left_brace), FadeOut(left_text),
            FadeOut(right_brace), FadeOut(right_text),
            step_text.animate.become(
                Text("Recursion: Quicksort Left and Right subarrays to get fully sorted array", font_size=17, color=BLUE_B).to_edge(DOWN, buff=0.3)
            )
        )

        # In left subarray [7, 20, 10, 30], sort 20 and 10
        pos_1 = curr_lbls[1].get_center()
        pos_2 = curr_lbls[2].get_center()
        self.play(
            curr_lbls[1].animate.move_to(pos_2),
            curr_lbls[2].animate.move_to(pos_1),
            run_time=1.0
        )
        curr_vals[1], curr_vals[2] = curr_vals[2], curr_vals[1]
        curr_lbls[1], curr_lbls[2] = curr_lbls[2], curr_lbls[1]

        # Turn all boxes green to signify fully sorted!
        self.play(*[b.animate.set_fill(GREEN_D, opacity=0.85) for b in boxes], run_time=1.2)

        final_summary = Text("Array Fully Sorted: [7, 10, 20, 30, 40, 50, 60, 80, 100]", font_size=20, color=GREEN)
        final_summary.next_to(step_text, UP, buff=0.25)
        self.play(Write(final_summary))
        self.wait(2.5)


if __name__ == "__main__":
    import sys
    import subprocess
    cmd = [sys.executable, "-m", "manim", "-ql", __file__, "QuickSortFullScene"]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)
