"""
MANIM COMMUNITY EDITION -- COMPLETE API REFERENCE WITH WORKING CODE
====================================================================
Extracted directly from the installed manim source code (v0.18+).

Every class, every animation type, every Mobject, every method -- all verified
against the actual source at:
  .venv/lib/python3.11/site-packages/manim/

IMPORTANT NOTES FOR MANIM CE vs MANIMLIB (3b1b):
  - Use `Create` not `ShowCreation`
  - Use `axes.plot(func)` not `axes.get_graph(func)`
  - Use `MoveToTarget` not `ApplyMethod` for simple transforms
  - Use `.animate` syntax: `mob.animate.shift(RIGHT)` is preferred
  - `TransformMatchingTex` uses `{{}}` braces for matching
  - `FadeIn`/`FadeOut` support `shift=` and `scale=` and `target_position=`
  - `Write` works for both Text and VMobject
  - `ParametricFunction` uses `t_range=` not `t_min`/`t_max`

Table of Contents:
  1.  CREATION ANIMATIONS
  2.  TRANSFORM ANIMATIONS
  3.  FADING ANIMATIONS
  4.  INDICATION ANIMATIONS
  5.  GROWING ANIMATIONS
  6.  MOVEMENT ANIMATIONS
  7.  ROTATION ANIMATIONS
  8.  COMPOSITION ANIMATIONS
  9.  NUMBER ANIMATIONS
  10. SPECIALIZED ANIMATIONS
  11. UPDATER ANIMATIONS
  12. CHANGING / TRACED PATH
  13. GEOMETRY: ARCS & CIRCLES
  14. GEOMETRY: LINES & ARROWS
  15. GEOMETRY: POLYGRAMS & SHAPES
  16. GEOMETRY: SHAPE MATCHERS
  17. TEXT: TEX & MATHTEX
  18. TEXT: TEXT MOBJECT
  19. TEXT: NUMBERS
  20. TABLES
  21. COORDINATE SYSTEMS: AXES
  22. COORDINATE SYSTEMS: THREEDAXES
  23. COORDINATE SYSTEMS: NUMBERPLANE
  24. COORDINATE SYSTEMS: POLARPLANE
  25. COORDINATE SYSTEMS: COMPLEXPLANE
  26. GRAPHING: PLOT METHODS (every method)
  27. GRAPHING: NUMBER LINE
  28. GRAPHING: BAR CHART
  29. VALUE TRACKER PATTERNS
  30. GRAPH THEORY: GRAPH & DIGRAPH
  31. 3D MOBJECTS
  32. 3D CAMERA TECHNIQUES
  33. SVG & IMAGE MOBJECTS
  34. VECTOR FIELDS
  35. MATRIX MOBJECT
  36. BRACE MOBJECT
  37. BOOLEAN OPS
  38. CODE MOBJECT
"""

from manim import *
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CREATION ANIMATIONS
# Source: manim/animation/creation.py
# Classes: Create, Uncreate, DrawBorderThenFill, Write, Unwrite,
#          ShowPartial, ShowIncreasingSubsets, SpiralIn,
#          AddTextLetterByLetter, RemoveTextLetterByLetter,
#          ShowSubmobjectsOneByOne, AddTextWordByWord,
#          TypeWithCursor, UntypeWithCursor
# ═══════════════════════════════════════════════════════════════════════════════

class CreationExamples(Scene):
    def construct(self):
        # --- Create: Incrementally draws a VMobject ---
        sq = Square(color=BLUE)
        self.play(Create(sq))                      # draws stroke progressively
        self.play(Uncreate(sq))                     # reverse of Create

        # --- DrawBorderThenFill: draws border first, then fills ---
        sq2 = Square(fill_opacity=1, fill_color=ORANGE)
        self.play(DrawBorderThenFill(sq2))

        # --- Write: simulates hand-writing (text or VMobject) ---
        text = Text("Hello Manim", font_size=48)
        self.play(Write(text))
        self.play(Unwrite(text))                    # erases in reverse

        # --- Write with reverse ---
        text2 = Text("Goodbye", font_size=48)
        self.play(Write(text2, reverse=True, remover=False))

        # --- SpiralIn: sub-mobjects fly in on spiral paths ---
        shapes = VGroup(
            MathTex(r"\pi").scale(3),
            Circle(color=GREEN, fill_opacity=1),
            Square(color=BLUE, fill_opacity=1),
        )
        self.play(SpiralIn(shapes))

        # --- ShowIncreasingSubsets: reveal submobjects one by one, cumulative ---
        dots = VGroup(*[Dot() for _ in range(10)]).arrange(RIGHT)
        self.add(dots)
        self.play(ShowIncreasingSubsets(dots), run_time=2)

        # --- ShowSubmobjectsOneByOne: show one at a time, hiding previous ---
        squares = VGroup(*[Square(color=c) for c in [RED, GREEN, BLUE]])
        squares.arrange(RIGHT)
        self.play(ShowSubmobjectsOneByOne(squares), run_time=3)

        # --- AddTextLetterByLetter (Text only, not MathTex) ---
        letter_text = Text("TypeWriter", font_size=48)
        self.play(AddTextLetterByLetter(letter_text, time_per_char=0.1))
        self.play(RemoveTextLetterByLetter(letter_text, time_per_char=0.05))

        # --- TypeWithCursor ---
        cursor_text = Text("Inserting", color=PURPLE).scale(1.5)
        cursor = Rectangle(
            color=GREY_A, fill_color=GREY_A, fill_opacity=1.0,
            height=1.1, width=0.5,
        ).move_to(cursor_text[0])
        self.play(TypeWithCursor(cursor_text, cursor))
        self.play(Blink(cursor, blinks=2))

        # --- UntypeWithCursor ---
        del_text = Text("Deleting", color=PURPLE).scale(1.5)
        cursor2 = Rectangle(
            color=GREY_A, fill_color=GREY_A, fill_opacity=1.0,
            height=1.1, width=0.5,
        ).move_to(del_text[0])
        self.play(UntypeWithCursor(del_text, cursor2))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TRANSFORM ANIMATIONS
# Source: manim/animation/transform.py
# Classes: Transform, ReplacementTransform, TransformFromCopy,
#          ClockwiseTransform, CounterclockwiseTransform,
#          MoveToTarget, ApplyMethod, ApplyPointwiseFunction,
#          FadeToColor, FadeTransform, FadeTransformPieces,
#          ScaleInPlace, ShrinkToCenter, Restore,
#          ApplyFunction, ApplyMatrix, ApplyComplexFunction,
#          CyclicReplace, Swap
#
# Source: manim/animation/transform_matching_parts.py
# Classes: TransformMatchingShapes, TransformMatchingTex
# ═══════════════════════════════════════════════════════════════════════════════

class TransformExamples(Scene):
    def construct(self):
        # --- Transform: morphs mobject into target ---
        sq = Square()
        circ = Circle()
        self.play(Transform(sq, circ))
        # Note: sq is now visually a circle, but sq is still in the scene
        # (not circ). circ was never added.

        # --- ReplacementTransform: replaces source with target in scene ---
        a = Square(color=RED)
        b = Circle(color=BLUE)
        self.play(ReplacementTransform(a, b))
        # Now b is in the scene, a is removed

        # --- TransformFromCopy: keeps original, transforms a copy ---
        original = Text("Original")
        copy_target = Text("Copy").shift(DOWN * 2)
        self.add(original)
        self.play(TransformFromCopy(original, copy_target))
        # Both original and copy_target remain

        # --- ClockwiseTransform / CounterclockwiseTransform ---
        d1, d2 = Dot(LEFT * 2), Dot(RIGHT * 2)
        self.play(ClockwiseTransform(d1, d2))       # path_arc = -PI
        self.play(CounterclockwiseTransform(d1, d2)) # path_arc = PI

        # --- MoveToTarget ---
        c = Circle()
        c.generate_target()
        c.target.set_fill(color=GREEN, opacity=0.5)
        c.target.shift(2 * RIGHT + UP).scale(0.5)
        self.add(c)
        self.play(MoveToTarget(c))

        # --- .animate syntax (preferred over ApplyMethod) ---
        sq2 = Square()
        self.play(sq2.animate.shift(RIGHT * 2).set_color(RED).scale(0.5))

        # --- ApplyPointwiseFunction ---
        sq3 = Square()
        self.play(
            ApplyPointwiseFunction(
                lambda p: complex_to_R3(np.exp(R3_to_complex(p))),
                sq3,
            )
        )

        # --- FadeToColor ---
        txt = Text("Color Change")
        self.play(FadeToColor(txt, color=RED))

        # --- ScaleInPlace ---
        self.play(ScaleInPlace(txt, 2))

        # --- ShrinkToCenter ---
        self.play(ShrinkToCenter(txt))

        # --- Restore (requires save_state first) ---
        s = Square()
        s.save_state()
        self.play(FadeIn(s))
        self.play(s.animate.set_color(PURPLE).shift(2 * LEFT).scale(3))
        self.play(Restore(s), run_time=2)

        # --- FadeTransform: fades one into another ---
        rect = Rectangle(width=4, height=1)
        circ2 = Circle(fill_opacity=1).scale(0.25)
        self.play(FadeTransform(rect, circ2, stretch=True))

        # --- FadeTransformPieces: submobjects match piecewise ---
        src = VGroup(Square(), Circle().shift(LEFT + UP))
        tgt = VGroup(Circle(), Triangle().shift(RIGHT + DOWN))
        self.play(FadeTransformPieces(src, tgt))

        # --- ApplyMatrix: apply a linear transformation matrix ---
        matrix = [[1, 1], [0, 2/3]]
        plane = NumberPlane()
        self.play(ApplyMatrix(matrix, plane))

        # --- ApplyComplexFunction ---
        plane2 = NumberPlane()
        self.play(ApplyComplexFunction(lambda z: z**2, plane2))

        # --- CyclicReplace / Swap ---
        group = VGroup(Square(), Circle(), Triangle(), Star())
        group.arrange(RIGHT)
        self.add(group)
        self.play(CyclicReplace(*group))
        self.play(Swap(group[0], group[1]))

        # --- TransformMatchingShapes ---
        src_txt = Text("the morse code")
        tar_txt = Text("here come dots")
        self.play(Write(src_txt))
        self.play(TransformMatchingShapes(src_txt, tar_txt, path_arc=PI/2))

        # --- TransformMatchingTex ---
        eq1 = MathTex("{{x}}^2", "+", "{{y}}^2", "=", "{{z}}^2")
        eq2 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")
        self.play(TransformMatchingTex(eq1, eq2))

        # --- Transform with path_arc ---
        left_c = Circle(color=BLUE, fill_opacity=1, radius=0.5).shift(LEFT * 2)
        right_c = left_c.copy().shift(4 * RIGHT)
        self.play(Transform(left_c, right_c, path_arc=90 * DEGREES))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FADING ANIMATIONS
# Source: manim/animation/fading.py
# Classes: FadeIn, FadeOut
# ═══════════════════════════════════════════════════════════════════════════════

class FadingExamples(Scene):
    def construct(self):
        tex = Tex("Fade", "In").scale(3)

        # --- Basic FadeIn ---
        self.play(FadeIn(tex))

        # --- FadeIn with shift ---
        self.play(FadeIn(tex, shift=DOWN))

        # --- FadeIn with scale ---
        self.play(FadeIn(tex, scale=0.66))

        # --- FadeIn with target_position (fades in from another mobject's location) ---
        dot = Dot(UP * 2 + LEFT)
        self.play(FadeIn(tex, target_position=dot))

        # --- FadeOut with shift ---
        self.play(FadeOut(tex, shift=DOWN * 2))

        # --- FadeOut with scale ---
        self.play(FadeOut(tex, scale=1.5))

        # --- FadeOut to target_position ---
        self.play(FadeOut(tex, target_position=dot))

        # --- Multiple mobjects at once ---
        self.play(FadeIn(tex[0]), FadeIn(tex[1], shift=DOWN))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INDICATION ANIMATIONS
# Source: manim/animation/indication.py
# Classes: FocusOn, Indicate, Flash, ShowPassingFlash,
#          ShowPassingFlashWithThinningStrokeWidth,
#          ApplyWave, Circumscribe, Wiggle, Blink
# ═══════════════════════════════════════════════════════════════════════════════

class IndicationExamples(Scene):
    def construct(self):
        tex = Tex("Attention").scale(2)
        self.add(tex)

        # --- Indicate: temporarily scale + recolor ---
        self.play(Indicate(tex))
        self.play(Indicate(tex, scale_factor=1.5, color=RED))

        # --- FocusOn: shrinking spotlight to a point ---
        dot = Dot(color=YELLOW).shift(DOWN)
        self.add(dot)
        self.play(FocusOn(dot))

        # --- Flash: radiating lines from a point ---
        self.play(Flash(dot))
        self.play(Flash(
            dot, line_length=0.5, num_lines=20,
            color=RED, flash_radius=0.5 + SMALL_BUFF,
        ))

        # --- ShowPassingFlash: a sliver traveling along the stroke ---
        polygon = RegularPolygon(5, color=BLUE, stroke_width=6).scale(2)
        self.add(polygon)
        self.play(ShowPassingFlash(polygon.copy().set_color(YELLOW), time_width=0.5))

        # --- ApplyWave: wave distortion ---
        self.play(ApplyWave(tex))
        self.play(ApplyWave(tex, direction=RIGHT, time_width=0.5, amplitude=0.3))
        self.play(ApplyWave(tex, rate_func=linear, ripples=4))

        # --- Wiggle ---
        self.play(Wiggle(tex))

        # --- Circumscribe: temporary surrounding shape ---
        self.play(Circumscribe(tex))                    # Rectangle
        self.play(Circumscribe(tex, Circle))            # Circle
        self.play(Circumscribe(tex, fade_out=True))     # fades out
        self.play(Circumscribe(tex, Circle, True))      # fade_in=True
        self.play(Circumscribe(tex, time_width=2))      # longer time_width

        # --- Blink: toggle visibility ---
        text = Text("Blinking").scale(1.5)
        self.add(text)
        self.play(Blink(text, blinks=3))


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GROWING ANIMATIONS
# Source: manim/animation/growing.py
# Classes: GrowFromPoint, GrowFromCenter, GrowFromEdge,
#          GrowArrow, SpinInFromNothing
# ═══════════════════════════════════════════════════════════════════════════════

class GrowingExamples(Scene):
    def construct(self):
        # --- GrowFromPoint ---
        sq = Square()
        self.play(GrowFromPoint(sq, ORIGIN))
        self.play(GrowFromPoint(Square(), [-2, 2, 0]))
        self.play(GrowFromPoint(Square(), [3, -2, 0], RED))  # with point_color

        # --- GrowFromCenter ---
        circ = Circle()
        self.play(GrowFromCenter(circ))
        self.play(GrowFromCenter(Square(), point_color=RED))

        # --- GrowFromEdge ---
        self.play(GrowFromEdge(Square(), DOWN))
        self.play(GrowFromEdge(Square(), RIGHT))
        self.play(GrowFromEdge(Square(), UR))

        # --- GrowArrow ---
        arrow = Arrow(2 * LEFT, 2 * RIGHT)
        self.play(GrowArrow(arrow))

        # --- SpinInFromNothing ---
        star = Star()
        self.play(SpinInFromNothing(star))
        self.play(SpinInFromNothing(Square(), angle=2 * PI))


# ═══════════════════════════════════════════════════════════════════════════════
# 6. MOVEMENT ANIMATIONS
# Source: manim/animation/movement.py
# Classes: Homotopy, SmoothedVectorizedHomotopy, ComplexHomotopy,
#          PhaseFlow, MoveAlongPath
# ═══════════════════════════════════════════════════════════════════════════════

class MovementExamples(Scene):
    def construct(self):
        # --- Homotopy: (x,y,z,t) -> (x',y',z') ---
        square = Square()
        def homotopy(x, y, z, t):
            return (x + t * 2, y + 0.2 * np.sin(x + 10 * t), z)
        self.play(Homotopy(homotopy, square, run_time=2, rate_func=linear))

        # --- ComplexHomotopy ---
        circ = Circle()
        def complex_homotopy(z, t):
            return z * np.exp(1j * t * PI)
        self.play(ComplexHomotopy(complex_homotopy, circ, run_time=2))

        # --- MoveAlongPath ---
        dot = Dot(color=ORANGE)
        line = Line(LEFT * 3, RIGHT * 3)
        self.add(line)
        self.play(MoveAlongPath(dot, line), rate_func=linear)

        # MoveAlongPath with a curved path
        path = Circle(radius=2)
        dot2 = Dot(color=RED)
        self.play(MoveAlongPath(dot2, path), run_time=3, rate_func=linear)

        # --- PhaseFlow ---
        plane = NumberPlane()
        self.add(plane)
        self.play(PhaseFlow(lambda p: np.array([-p[1], p[0], 0]), plane))


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ROTATION ANIMATIONS
# Source: manim/animation/rotation.py
# Classes: Rotating, Rotate
# ═══════════════════════════════════════════════════════════════════════════════

class RotationExamples(Scene):
    def construct(self):
        # --- Rotate: Transform-based (smooth interpolation to target) ---
        sq = Square(side_length=0.5).shift(UP * 2)
        self.play(
            Rotate(sq, angle=2 * PI, about_point=ORIGIN, rate_func=linear),
        )

        # Rotate in place
        sq2 = Square()
        self.play(Rotate(sq2, angle=PI))

        # --- Rotating: continuous rotation (good for long spins) ---
        arrow = Arrow(ORIGIN, RIGHT, color=GOLD)
        self.add(arrow)
        self.play(Rotating(arrow, angle=PI, about_point=ORIGIN, run_time=2))

        # 3D rotation
        # self.play(Rotating(cube, PI, axis=UP, about_point=ORIGIN))


# ═══════════════════════════════════════════════════════════════════════════════
# 8. COMPOSITION ANIMATIONS
# Source: manim/animation/composition.py
# Classes: AnimationGroup, Succession, LaggedStart, LaggedStartMap
# ═══════════════════════════════════════════════════════════════════════════════

class CompositionExamples(Scene):
    def construct(self):
        # --- AnimationGroup: play multiple animations simultaneously ---
        sq, circ = Square(), Circle()
        sq.shift(LEFT * 2); circ.shift(RIGHT * 2)
        self.play(AnimationGroup(
            Create(sq), Create(circ),
            lag_ratio=0,    # 0 = simultaneous
        ))

        # --- AnimationGroup with lag_ratio ---
        self.play(AnimationGroup(
            FadeIn(sq, shift=UP), FadeIn(circ, shift=UP),
            lag_ratio=0.5,  # second starts at 50% of first
        ))

        # --- Succession: play animations one after another ---
        dots = [Dot(point=p) for p in [UL * 2, DL * 2, DR * 2, UR * 2]]
        self.add(*dots)
        self.play(Succession(
            dots[0].animate.move_to(dots[1]),
            dots[1].animate.move_to(dots[2]),
            dots[2].animate.move_to(dots[3]),
        ))

        # --- LaggedStart: staggered start with lag_ratio ---
        group = VGroup(*[Dot(radius=0.16) for _ in range(5)]).arrange(RIGHT)
        self.play(LaggedStart(
            *[dot.animate.shift(UP * 2) for dot in group],
            lag_ratio=0.25,
            run_time=3,
        ))

        # --- LaggedStartMap: map an animation to each submobject ---
        dots_grid = VGroup(
            *[Dot(radius=0.16) for _ in range(35)]
        ).arrange_in_grid(rows=5, cols=7, buff=MED_LARGE_BUFF)
        self.add(dots_grid)
        self.play(LaggedStartMap(FadeIn, dots_grid, lag_ratio=0.1, run_time=2))

        # LaggedStartMap with arg_creator
        self.play(LaggedStartMap(
            ApplyMethod, dots_grid,
            lambda m: (m.set_color, YELLOW),
            lag_ratio=0.05,
            rate_func=there_and_back,
            run_time=2,
        ))


# ═══════════════════════════════════════════════════════════════════════════════
# 9. NUMBER ANIMATIONS
# Source: manim/animation/numbers.py
# Classes: ChangingDecimal, ChangeDecimalToValue
# ═══════════════════════════════════════════════════════════════════════════════

class NumberAnimationExamples(Scene):
    def construct(self):
        # --- ChangingDecimal: animate by a function of alpha ---
        number = DecimalNumber(0, font_size=48)
        self.add(number)
        self.play(ChangingDecimal(number, lambda a: 100 * a), run_time=3)

        # --- ChangeDecimalToValue: linear interpolation to target ---
        number2 = DecimalNumber(0, font_size=48).shift(DOWN)
        self.add(number2)
        self.play(ChangeDecimalToValue(number2, 42, run_time=2))


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SPECIALIZED ANIMATIONS
# Source: manim/animation/specialized.py
# Classes: Broadcast
# ═══════════════════════════════════════════════════════════════════════════════

class SpecializedExamples(Scene):
    def construct(self):
        # --- Broadcast: expanding rings from a focal point ---
        mob = Circle(radius=2, color=TEAL_A)
        self.play(Broadcast(mob))

        # Custom broadcast
        self.play(Broadcast(
            Circle(radius=3, color=RED),
            n_mobs=8,
            initial_opacity=1,
            final_opacity=0,
            run_time=4,
        ))


# ═══════════════════════════════════════════════════════════════════════════════
# 11. UPDATER ANIMATIONS
# Source: manim/animation/updaters/update.py
# Classes: UpdateFromFunc, UpdateFromAlphaFunc, MaintainPositionRelativeTo
#
# Source: manim/animation/updaters/mobject_update_utils.py
# Functions: always_redraw, always_shift, always_rotate, always, f_always
# ═══════════════════════════════════════════════════════════════════════════════

class UpdaterExamples(Scene):
    def construct(self):
        # --- UpdateFromFunc: update mobject each frame by a function ---
        dot = Dot(color=RED)
        self.play(UpdateFromFunc(
            dot,
            lambda m: m.shift(RIGHT * 0.05),
            run_time=3,
        ))

        # --- UpdateFromAlphaFunc: func receives (mobject, alpha) ---
        sq = Square()
        self.play(UpdateFromAlphaFunc(
            sq,
            lambda m, a: m.set_opacity(a),
            run_time=2,
        ))

        # --- always_redraw: rebuild mobject every frame ---
        tracker = ValueTracker(0)
        line = always_redraw(
            lambda: Line(ORIGIN, RIGHT * tracker.get_value(), color=BLUE)
        )
        self.add(line)
        self.play(tracker.animate.set_value(4), run_time=2)

        # --- always_shift: continuous shifting ---
        dot2 = Dot(color=GREEN)
        always_shift(dot2, direction=RIGHT, rate=0.5)
        self.add(dot2)
        self.wait(3)

        # --- always_rotate: continuous rotation ---
        sq2 = Square(color=ORANGE)
        always_rotate(sq2, rate=PI/2)  # 90 deg/sec
        self.add(sq2)
        self.wait(3)

        # --- .add_updater() directly ---
        pointer = Vector(DOWN)
        label = MathTex("x").add_updater(lambda m: m.next_to(pointer, UP))
        self.add(pointer, label)
        self.play(pointer.animate.shift(RIGHT * 3), run_time=2)

        # --- mob.always syntax ---
        dot3 = Dot()
        label2 = Text("here", font_size=20)
        label2.always.next_to(dot3, UP)
        self.add(dot3, label2)
        self.play(dot3.animate.shift(RIGHT * 2), run_time=2)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. CHANGING / TRACED PATH
# Source: manim/animation/changing.py
# Classes: AnimatedBoundary, TracedPath
# ═══════════════════════════════════════════════════════════════════════════════

class ChangingExamples(Scene):
    def construct(self):
        # --- AnimatedBoundary ---
        text = Text("So shiny!")
        boundary = AnimatedBoundary(text, colors=[RED, GREEN, BLUE], cycle_rate=3)
        self.add(text, boundary)
        self.wait(3)

        # --- TracedPath ---
        circ = Circle(color=RED).shift(4 * LEFT)
        dot = Dot(color=RED).move_to(circ.get_start())
        rolling = VGroup(circ, dot)
        trace = TracedPath(circ.get_start)
        rolling.add_updater(lambda m: m.rotate(-0.3))
        self.add(trace, rolling)
        self.play(rolling.animate.shift(8 * RIGHT), run_time=4, rate_func=linear)

        # --- TracedPath with dissipation ---
        a = Dot(RIGHT * 2)
        b = TracedPath(a.get_center, dissipating_time=0.5, stroke_opacity=[0, 1])
        self.add(a, b)
        self.play(a.animate(path_arc=PI/4).shift(LEFT * 2))


# ═══════════════════════════════════════════════════════════════════════════════
# 13. GEOMETRY: ARCS & CIRCLES
# Source: manim/mobject/geometry/arc.py
# Classes: Arc, ArcBetweenPoints, CurvedArrow, CurvedDoubleArrow,
#          Circle, Dot, AnnotationDot, LabeledDot, Ellipse,
#          AnnularSector, Sector, Annulus, CubicBezier,
#          ArcPolygon, ArcPolygonFromArcs, TangentialArc
# ═══════════════════════════════════════════════════════════════════════════════

class ArcExamples(Scene):
    def construct(self):
        # Basic shapes
        arc = Arc(radius=2, start_angle=0, angle=PI/2, color=BLUE)
        arc_between = ArcBetweenPoints(LEFT * 2, RIGHT * 2, angle=TAU/4)
        curved_arrow = CurvedArrow(2 * LEFT, 2 * RIGHT, radius=-5)
        curved_double = CurvedDoubleArrow(ORIGIN, 2 * RIGHT)

        circle = Circle(radius=1, color=RED)
        dot = Dot(color=YELLOW)
        annot_dot = AnnotationDot()
        labeled_dot = LabeledDot("A")
        labeled_dot_math = LabeledDot(MathTex(r"\alpha").set_color(ORANGE))

        ellipse = Ellipse(width=4, height=2, color=GREEN)
        sector = Sector(outer_radius=2, angle=PI/3, color=BLUE)
        annular = AnnularSector(inner_radius=1, outer_radius=2, angle=PI/2)
        annulus = Annulus(inner_radius=1, outer_radius=2, color=PURPLE)

        # ArcPolygon (polygon with curved sides)
        arc_poly = ArcPolygon(
            [-1, 0, 0], [0, 1.5, 0], [1, 0, 0],
            arc_config=[
                {"angle": PI/4},
                {"angle": PI/4},
                {"angle": PI/2},
            ],
        )

        VGroup(
            arc, arc_between, curved_arrow, circle, dot,
            annot_dot, labeled_dot, ellipse, sector, annulus,
        ).arrange_in_grid(rows=2, buff=1).scale(0.5)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. GEOMETRY: LINES & ARROWS
# Source: manim/mobject/geometry/line.py
# Classes: Line, DashedLine, TangentLine, Elbow,
#          Arrow, Vector, DoubleArrow, Angle, RightAngle
# ═══════════════════════════════════════════════════════════════════════════════

class LineExamples(Scene):
    def construct(self):
        line = Line(LEFT * 3, RIGHT * 3, color=BLUE)
        dashed = DashedLine(LEFT * 3, RIGHT * 3, color=GREEN)
        arrow = Arrow(LEFT * 2, RIGHT * 2, color=RED)
        vector = Vector(UP + RIGHT, color=YELLOW)
        double_arrow = DoubleArrow(LEFT * 2, RIGHT * 2, color=PURPLE)
        elbow = Elbow(width=0.5)

        # Angle between two lines
        l1 = Line(ORIGIN, RIGHT * 2)
        l2 = Line(ORIGIN, UP * 2 + RIGHT)
        angle = Angle(l1, l2, radius=0.5, color=GREEN)
        right_angle = RightAngle(l1, Line(ORIGIN, UP * 2), length=0.3)

        # TangentLine to a circle
        circ = Circle(radius=2)
        tangent = TangentLine(circ, alpha=0.25, length=4, color=ORANGE)

        VGroup(
            line, dashed, arrow, vector, double_arrow,
            VGroup(l1, l2, angle), VGroup(circ, tangent),
        ).arrange_in_grid(rows=2, buff=1).scale(0.5)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. GEOMETRY: POLYGRAMS & SHAPES
# Source: manim/mobject/geometry/polygram.py
# Classes: Polygram, Polygon, RegularPolygram, RegularPolygon,
#          Star, Triangle, Rectangle, Square, RoundedRectangle,
#          Cutout, ConvexHull
# ═══════════════════════════════════════════════════════════════════════════════

class ShapeExamples(Scene):
    def construct(self):
        polygon = Polygon([-1, -1, 0], [1, -1, 0], [0, 1, 0], color=BLUE)
        reg_polygon = RegularPolygon(n=6, color=GREEN)
        star = Star(n=5, color=YELLOW)
        triangle = Triangle(color=RED)
        rectangle = Rectangle(width=3, height=1, color=PURPLE)
        square = Square(side_length=1.5, color=ORANGE)
        rounded_rect = RoundedRectangle(corner_radius=0.3, width=3, height=1)

        # Cutout: shape with holes
        outer = Square(side_length=3, fill_opacity=1, color=BLUE)
        inner = Circle(radius=0.5)
        cutout = Cutout(outer, inner, fill_opacity=1, color=BLUE)

        VGroup(
            polygon, reg_polygon, star, triangle,
            rectangle, square, rounded_rect, cutout,
        ).arrange_in_grid(rows=2, buff=0.5).scale(0.5)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. GEOMETRY: SHAPE MATCHERS
# Source: manim/mobject/geometry/shape_matchers.py
# Classes: SurroundingRectangle, BackgroundRectangle, Cross, Underline
# ═══════════════════════════════════════════════════════════════════════════════

class ShapeMatcherExamples(Scene):
    def construct(self):
        text = Text("Important")
        sr = SurroundingRectangle(text, color=YELLOW, buff=0.2)
        sr_rounded = SurroundingRectangle(text, corner_radius=0.2)
        bg = BackgroundRectangle(text, color=BLACK, fill_opacity=0.8)
        cross = Cross(text, color=RED)
        underline = Underline(text, color=BLUE)

        self.add(text, sr, underline)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. TEXT: TEX & MATHTEX
# Source: manim/mobject/text/tex_mobject.py
# Classes: SingleStringMathTex, MathTex, Tex, BulletedList, Title
# ═══════════════════════════════════════════════════════════════════════════════

class TexExamples(Scene):
    def construct(self):
        # --- MathTex (math mode) ---
        eq = MathTex(r"e^{i\pi} + 1 = 0")

        # MathTex with separate substrings for animation
        eq2 = MathTex("x^2", "+", "y^2", "=", "z^2")
        # Access: eq2[0] is "x^2", eq2[2] is "y^2", etc.

        # MathTex with {{ }} for TransformMatchingTex
        eq3 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")

        # --- Tex (text mode with optional math) ---
        txt = Tex("Hello ", r"$\alpha$", " World")

        # --- BulletedList ---
        bl = BulletedList("First", "Second", "Third")

        # --- Title ---
        title = Title("My Title", include_underline=True)

        VGroup(eq, eq2, txt, bl, title).arrange(DOWN, buff=0.5).scale(0.7)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. TEXT: TEXT MOBJECT
# Source: manim/mobject/text/text_mobject.py
# Classes: Text, MarkupText, Paragraph
# ═══════════════════════════════════════════════════════════════════════════════

class TextExamples(Scene):
    def construct(self):
        # --- Text (Pango/Cairo rendered) ---
        t1 = Text("Hello World", font_size=48, color=WHITE)
        t2 = Text("Bold", weight="BOLD", font_size=36)
        t3 = Text("Italic", slant="ITALIC", font_size=36)
        t4 = Text(
            "Gradient", font_size=48,
            gradient=(RED, BLUE),
        )
        t5 = Text("Custom Font", font="Courier", font_size=36)

        # Coloring specific parts
        t6 = Text("Hello World", font_size=36)
        t6[0:5].set_color(RED)   # "Hello"
        t6[5:].set_color(BLUE)   # " World"

        # --- MarkupText (Pango markup) ---
        mt = MarkupText(
            '<span foreground="red">Red</span> and <b>Bold</b>',
            font_size=36,
        )

        VGroup(t1, t2, t3, t4, t5, t6, mt).arrange(DOWN, buff=0.3).scale(0.6)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. TEXT: NUMBERS
# Source: manim/mobject/text/numbers.py
# Classes: DecimalNumber, Integer
# ═══════════════════════════════════════════════════════════════════════════════

class NumberMobjectExamples(Scene):
    def construct(self):
        d = DecimalNumber(3.14159, num_decimal_places=3, font_size=48)
        i = Integer(42, font_size=48)

        # DecimalNumber tracks a value and can be animated
        tracker = ValueTracker(0)
        num = DecimalNumber(font_size=48)
        num.add_updater(lambda m: m.set_value(tracker.get_value()))
        self.add(num)
        self.play(tracker.animate.set_value(100), run_time=3)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. TABLES
# Source: manim/mobject/table.py
# Classes: Table, MathTable, MobjectTable, IntegerTable, DecimalTable
# ═══════════════════════════════════════════════════════════════════════════════

class TableExamples(Scene):
    def construct(self):
        # --- Basic Table ---
        t0 = Table(
            [["First", "Second"], ["Third", "Fourth"]],
            row_labels=[Text("R1"), Text("R2")],
            col_labels=[Text("C1"), Text("C2")],
            top_left_entry=Text("TOP"),
        )
        t0.add_highlighted_cell((2, 2), color=GREEN)

        # --- MathTable ---
        t1 = MathTable(
            [["+", 0, 5, 10],
             [0, 0, 5, 10],
             [2, 2, 7, 12]],
            include_outer_lines=True,
        )

        # --- DecimalTable ---
        x_vals = np.linspace(-2, 2, 5)
        y_vals = np.exp(x_vals)
        t2 = DecimalTable(
            [x_vals, y_vals],
            row_labels=[MathTex("x"), MathTex("f(x)")],
            include_outer_lines=True,
        )

        # --- MobjectTable ---
        circle = Circle(color=RED).scale(0.3)
        square = Square(color=BLUE).scale(0.3)
        t3 = MobjectTable(
            [[circle.copy(), square.copy()],
             [square.copy(), circle.copy()]],
        )

        # --- IntegerTable ---
        vals = np.arange(1, 13).reshape(3, 4)
        t4 = IntegerTable(vals, include_outer_lines=True)

        # --- Table methods ---
        # t.get_cell((row, col))
        # t.get_horizontal_lines()
        # t.get_vertical_lines()
        # t.get_row(n)
        # t.get_columns()
        # t.get_entries()
        # t.get_entries_without_labels()
        # t.add_highlighted_cell((row, col), color=)

        Group(t0, t2, t3).scale(0.35).arrange(RIGHT, buff=0.5)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. COORDINATE SYSTEMS: AXES
# Source: manim/mobject/graphing/coordinate_systems.py -> class Axes
# ═══════════════════════════════════════════════════════════════════════════════

class AxesExamples(Scene):
    def construct(self):
        # --- Basic Axes ---
        ax = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 0.5],
            x_length=10,
            y_length=5,
            axis_config={"include_numbers": True, "font_size": 24},
            tips=True,
        )

        # --- Axis Labels ---
        labels = ax.get_axis_labels(
            x_label=MathTex("x"),
            y_label=MathTex("f(x)"),
        )

        # --- Individual axis labels ---
        x_lbl = ax.get_x_axis_label(Tex("time"), edge=DOWN, direction=DOWN)
        y_lbl = ax.get_y_axis_label(Tex("value"), edge=LEFT, direction=LEFT)

        # --- Add coordinates (numbers on axes) ---
        ax.add_coordinates()

        # --- Custom coordinate labels ---
        ax2 = Axes(x_range=[0, 7])
        x_dict = dict(zip(range(1, 8), [
            "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
        ]))
        ax2.add_coordinates(x_dict)

        # --- Log scale ---
        ax3 = Axes(
            x_range=[0, 10, 1],
            y_range=[-2, 6, 1],
            tips=False,
            axis_config={"include_numbers": True},
            y_axis_config={"scaling": LogBase(custom_labels=True)},
        )

        # --- Axes with custom tip shape ---
        ax4 = Axes(axis_config={"tip_shape": StealthTip})

        self.add(ax, labels)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. COORDINATE SYSTEMS: THREEDAXES
# Source: manim/mobject/graphing/coordinate_systems.py -> class ThreeDAxes
# ═══════════════════════════════════════════════════════════════════════════════

class ThreeDAxesExample(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-3, 3, 1],
        )
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)

        # z-axis label
        z_label = axes.get_z_axis_label(Tex("$z$"))

        # Plot a 3D surface
        surface = axes.plot_surface(
            lambda u, v: 2 * np.sin(u) + 2 * np.cos(v),
            u_range=(-3, 3),
            v_range=(-3, 3),
            resolution=(16, 16),
            colorscale=[BLUE, GREEN, YELLOW, ORANGE, RED],
        )

        self.add(axes, z_label, surface)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. COORDINATE SYSTEMS: NUMBERPLANE
# Source: manim/mobject/graphing/coordinate_systems.py -> class NumberPlane
# ═══════════════════════════════════════════════════════════════════════════════

class NumberPlaneExamples(Scene):
    def construct(self):
        plane = NumberPlane(
            x_range=(-5, 5, 1),
            y_range=(-4, 4, 1),
            background_line_style={
                "stroke_color": BLUE,
                "stroke_width": 1,
                "stroke_opacity": 0.4,
            },
        )
        self.add(plane)

        # NumberPlane inherits all Axes methods: plot(), c2p(), etc.
        graph = plane.plot(lambda x: np.sin(x), color=YELLOW)
        self.add(graph)

        # plot_line_graph
        line_graph = plane.plot_line_graph(
            x_values=[0, 1.5, 2, 2.8, 4],
            y_values=[1, 3, 2.25, 4, 2.5],
            line_color=GOLD_E,
            vertex_dot_style=dict(stroke_width=3, fill_color=PURPLE),
            stroke_width=4,
        )
        self.add(line_graph)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. COORDINATE SYSTEMS: POLARPLANE
# Source: manim/mobject/graphing/coordinate_systems.py -> class PolarPlane
# ═══════════════════════════════════════════════════════════════════════════════

class PolarPlaneExamples(Scene):
    def construct(self):
        polar = PolarPlane(azimuth_units="PI radians", size=6)
        self.add(polar)

        # Plot polar graph: r = f(theta)
        r = lambda theta: 2 * np.sin(theta * 5)
        graph = polar.plot_polar_graph(r, [0, 2 * PI], color=ORANGE)
        self.add(graph)

        # polar_to_point
        point = polar.polar_to_point(3, PI / 4)
        dot = Dot(point, color=RED)
        self.add(dot)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. COORDINATE SYSTEMS: COMPLEXPLANE
# Source: manim/mobject/graphing/coordinate_systems.py -> class ComplexPlane
# ═══════════════════════════════════════════════════════════════════════════════

class ComplexPlaneExamples(Scene):
    def construct(self):
        cp = ComplexPlane()
        self.add(cp)

        # number_to_point / point_to_number
        z = 2 + 1j
        pt = cp.number_to_point(z)
        dot = Dot(pt, color=YELLOW)
        label = MathTex("2+i", font_size=24).next_to(dot, UR)
        self.add(dot, label)


# ═══════════════════════════════════════════════════════════════════════════════
# 26. GRAPHING: ALL PLOT METHODS (comprehensive)
# Every method on CoordinateSystem/Axes for graphing
# ═══════════════════════════════════════════════════════════════════════════════

class AllPlotMethods(Scene):
    def construct(self):
        ax = Axes(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            x_length=10,
            y_length=5,
        )

        # ---- ax.plot(function, x_range, use_vectorized, colorscale) ----
        sine = ax.plot(lambda x: np.sin(x), color=BLUE)
        sine_partial = ax.plot(lambda x: np.sin(x), x_range=[-2, 2], color=RED)
        # With fine step for accuracy
        log_curve = ax.plot(
            lambda x: np.log(x),
            x_range=(0.001, 4, 0.001),
            color=GREEN,
        )
        # With smoothing disabled
        choppy = ax.plot(lambda x: np.sin(x), use_smoothing=False, color=ORANGE)
        # With colorscale (color by y-value)
        colored = ax.plot(
            lambda x: np.sin(x),
            x_range=[-4, 4],
            colorscale=[BLUE, GREEN, YELLOW, RED],
        )

        # ---- ax.plot_implicit_curve(func) ----
        implicit = ax.plot_implicit_curve(
            lambda x, y: y * (x - y) ** 2 - 4 * x - 8,
            color=BLUE,
        )

        # ---- ax.plot_parametric_curve(func) ----
        cardioid = ax.plot_parametric_curve(
            lambda t: np.array([
                np.exp(1) * np.cos(t) * (1 - np.cos(t)),
                np.exp(1) * np.sin(t) * (1 - np.cos(t)),
                0,
            ]),
            t_range=[0, 2 * PI],
            color="#0FF1CE",
        )

        # ---- ax.plot_line_graph(x_values, y_values) ----
        line_graph = ax.plot_line_graph(
            x_values=[0, 1, 2, 3, 4],
            y_values=[1, 2, 1.5, 3, 2],
            line_color=GOLD,
            add_vertex_dots=True,
            vertex_dot_radius=0.08,
        )

        # ---- ax.plot_derivative_graph(graph) ----
        parabola = ax.plot(lambda x: x ** 2, color=PURPLE_B)
        derivative = ax.plot_derivative_graph(parabola, color=GREEN)

        # ---- ax.plot_antiderivative_graph(graph) ----
        f = ax.plot(lambda x: (x ** 2 - 2) / 3, color=RED)
        antideriv = ax.plot_antiderivative_graph(f, color=BLUE)

        # ---- ax.get_area(graph, x_range, color, opacity, bounded_graph) ----
        curve = ax.plot(lambda x: 2 * np.sin(x), color=DARK_BLUE)
        area = ax.get_area(
            curve,
            x_range=(PI / 2, 3 * PI / 2),
            color=(GREEN_B, GREEN_D),
            opacity=0.5,
        )
        # Area between two curves
        upper = ax.plot(lambda x: x, color=BLUE)
        lower = ax.plot(lambda x: x ** 2 / 4, color=RED)
        between = ax.get_area(upper, x_range=[0, 3], bounded_graph=lower)

        # ---- ax.get_riemann_rectangles(graph, x_range, dx) ----
        quad = ax.plot(lambda x: 0.5 * x ** 2 - 0.5)
        rects = ax.get_riemann_rectangles(
            quad,
            x_range=[-3, 3],
            dx=0.25,
            color=(TEAL, BLUE_B, DARK_BLUE),
            input_sample_type="left",   # "left", "right", or "center"
            fill_opacity=0.6,
        )

        # ---- ax.get_vertical_line(point) ----
        pt = ax.coords_to_point(2, np.sin(2))
        v_line = ax.get_vertical_line(pt, line_config={"dashed_ratio": 0.85})

        # ---- ax.get_horizontal_line(point) ----
        h_line = ax.get_horizontal_line(pt, line_func=Line)

        # ---- ax.get_lines_to_point(point) ----
        lines = ax.get_lines_to_point(ax.c2p(2, 2))

        # ---- ax.get_graph_label(graph, label, x_val, direction) ----
        label = ax.get_graph_label(
            sine, label=MathTex(r"\sin(x)"),
            x_val=PI / 2, direction=UR, dot=True,
        )

        # ---- ax.get_T_label(x_val, graph, label) ----
        t_label = ax.get_T_label(x_val=2, graph=sine, label=Tex("x=2"))

        # ---- ax.get_secant_slope_group(x, graph, dx) ----
        slopes = ax.get_secant_slope_group(
            x=2.0,
            graph=quad,
            dx=1.0,
            dx_label=Tex("dx = 1.0"),
            dy_label="dy",
            secant_line_length=4,
            secant_line_color=RED_D,
        )

        # ---- ax.get_vertical_lines_to_graph(graph, x_range, num_lines) ----
        vert_lines = ax.get_vertical_lines_to_graph(
            sine, x_range=[0, 4], num_lines=30, color=BLUE,
        )

        # ---- Coordinate conversion ----
        # ax.coords_to_point(x, y) or ax.c2p(x, y)
        scene_point = ax.c2p(2, 3)
        # ax.point_to_coords(point) or ax.p2c(point)
        coords = ax.p2c(scene_point)
        # ax @ (x, y) shorthand
        scene_point2 = ax @ (1, 1, 0)
        # ax.input_to_graph_point(x, graph) or ax.i2gp(x, graph)
        graph_point = ax.i2gp(PI, sine)

        # ---- Slopes and tangents ----
        angle = ax.angle_of_tangent(x=3, graph=quad)
        slope = ax.slope_of_tangent(x=-2, graph=quad)

        self.add(ax, sine, area, rects, label)


# ═══════════════════════════════════════════════════════════════════════════════
# 27. GRAPHING: NUMBER LINE
# Source: manim/mobject/graphing/number_line.py
# Classes: NumberLine, UnitInterval
# ═══════════════════════════════════════════════════════════════════════════════

class NumberLineExamples(Scene):
    def construct(self):
        nl = NumberLine(
            x_range=[-5, 5, 1],
            length=10,
            include_numbers=True,
            include_tip=True,
            font_size=24,
        )

        # Custom tick marks
        nl2 = NumberLine(
            x_range=[0, 10, 2],
            numbers_with_elongated_ticks=[0, 5, 10],
            include_numbers=True,
        )

        # number_to_point / point_to_number
        pt = nl.number_to_point(3)
        dot = Dot(pt, color=RED)

        # n2p shorthand
        pt2 = nl.n2p(-2)

        # UnitInterval
        ui = UnitInterval()

        VGroup(nl, nl2, ui).arrange(DOWN, buff=1)
        self.add(nl, nl2, ui, dot)


# ═══════════════════════════════════════════════════════════════════════════════
# 28. GRAPHING: BAR CHART
# Source: manim/mobject/graphing/probability.py -> class BarChart
# ═══════════════════════════════════════════════════════════════════════════════

class BarChartExamples(Scene):
    def construct(self):
        chart = BarChart(
            values=[-5, 40, -10, 20, -3],
            bar_names=["one", "two", "three", "four", "five"],
            y_range=[-20, 50, 10],
            y_length=6,
            x_length=10,
            x_axis_config={"font_size": 24},
            bar_colors=[RED, BLUE, GREEN, YELLOW, PURPLE],
        )
        self.add(chart)

        # Get bar labels (numbers above bars)
        labels = chart.get_bar_labels(font_size=20)
        self.add(labels)

        # Change bar values (animatable)
        # chart.change_bar_values([10, 30, -5, 15, 25])

        # Access individual bars
        # chart.bars[0], chart.bars[1], etc.


# ═══════════════════════════════════════════════════════════════════════════════
# 29. VALUE TRACKER PATTERNS
# Source: manim/mobject/value_tracker.py
# Classes: ValueTracker, ComplexValueTracker
# ═══════════════════════════════════════════════════════════════════════════════

class ValueTrackerPatterns(Scene):
    def construct(self):
        # --- Pattern 1: ValueTracker + always_redraw for dynamic graphs ---
        ax = Axes(x_range=[-4, 4], y_range=[-2, 2], x_length=8, y_length=4)
        self.add(ax)

        k = ValueTracker(1)
        graph = always_redraw(
            lambda: ax.plot(
                lambda x: np.sin(k.get_value() * x),
                color=BLUE,
            )
        )
        k_label = always_redraw(
            lambda: MathTex(
                rf"k = {k.get_value():.2f}", font_size=30,
            ).to_corner(UR)
        )
        self.add(graph, k_label)
        self.play(k.animate.set_value(3), run_time=3)
        self.play(k.animate.set_value(0.5), run_time=2)

        # --- Pattern 2: ValueTracker + pointer on number line ---
        number_line = NumberLine()
        pointer = Vector(DOWN)
        label = MathTex("x").add_updater(lambda m: m.next_to(pointer, UP))
        tracker = ValueTracker(0)
        pointer.add_updater(
            lambda m: m.next_to(number_line.n2p(tracker.get_value()), UP)
        )
        self.add(number_line, pointer, label)
        self.play(tracker.animate.set_value(5), run_time=2)
        self.play(tracker.animate.set_value(-3), run_time=2)

        # --- Pattern 3: ValueTracker driving a Dot on a curve ---
        t = ValueTracker(0)
        curve = ax.plot(lambda x: x ** 2 / 4, color=GREEN)
        dot = always_redraw(
            lambda: Dot(ax.i2gp(t.get_value(), curve), color=RED)
        )
        tangent = always_redraw(
            lambda: ax.get_secant_slope_group(
                t.get_value(), curve, dx=0.01,
                secant_line_length=3, secant_line_color=YELLOW,
            )
        )
        self.add(curve, dot, tangent)
        self.play(t.animate.set_value(3), run_time=4, rate_func=linear)

        # --- Pattern 4: ComplexValueTracker ---
        complex_tracker = ComplexValueTracker(-2 + 1j)
        complex_dot = Dot().add_updater(
            lambda x: x.move_to(complex_tracker.points)
        )
        self.add(NumberPlane(), complex_dot)
        self.play(complex_tracker.animate.set_value(3 + 2j))
        self.play(complex_tracker.animate.set_value(
            complex_tracker.get_value() * 1j
        ))

        # --- Pattern 5: ValueTracker arithmetic ---
        vt = ValueTracker(10)
        vt += 5        # now 15
        vt -= 3        # now 12
        vt *= 2        # now 24
        vt /= 4        # now 6.0
        # self.play(vt.animate.increment_value(10))  # also works


# ═══════════════════════════════════════════════════════════════════════════════
# 30. GRAPH THEORY: GRAPH & DIGRAPH
# Source: manim/mobject/graph.py
# Classes: Graph, DiGraph
# ═══════════════════════════════════════════════════════════════════════════════

class GraphTheoryExamples(Scene):
    def construct(self):
        # --- Undirected Graph ---
        graph = Graph(
            vertices=[1, 2, 3, 4, 5],
            edges=[(1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (1, 3)],
            layout="circular",
            labels=True,
        )
        self.add(graph)

        # Available layouts: "circular", "kamada_kawai", "planar",
        # "random", "shell", "spectral", "spring", "tree",
        # "partite", "spiral", or a custom LayoutFunction

        # --- Directed Graph ---
        digraph = DiGraph(
            vertices=[1, 2, 3, 4],
            edges=[(1, 2), (2, 3), (3, 4), (4, 1)],
            layout="circular",
            labels=True,
        )

        # --- Change layout ---
        # graph.change_layout("spring")

        # --- Access vertices and edges ---
        # graph.vertices[1]  -> the Dot mobject for vertex 1
        # graph.edges[(1,2)] -> the Line mobject for edge (1,2)

        # --- Custom vertex/edge config ---
        custom_graph = Graph(
            [1, 2, 3],
            [(1, 2), (2, 3)],
            vertex_config={1: {"color": RED}, 2: {"color": GREEN}},
            edge_config={(1, 2): {"color": YELLOW, "stroke_width": 5}},
            labels=True,
            layout="spring",
        )

        VGroup(graph, digraph, custom_graph).arrange(RIGHT, buff=1).scale(0.5)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 31. 3D MOBJECTS
# Source: manim/mobject/three_d/three_dimensions.py
# Classes: Surface, Sphere, Dot3D, Cube, Prism, Cone,
#          Arrow3D, Cylinder, Line3D, Torus
#
# Source: manim/mobject/three_d/polyhedra.py
# Classes: Polyhedron, Tetrahedron, Octahedron, Icosahedron, Dodecahedron
# ═══════════════════════════════════════════════════════════════════════════════

class ThreeDMobjectExamples(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)

        axes = ThreeDAxes()
        cube = Cube(side_length=1, fill_opacity=0.7)
        sphere = Sphere(radius=0.5).shift(RIGHT * 2)
        cone = Cone().shift(LEFT * 2)
        cylinder = Cylinder(radius=0.3, height=1).shift(UP * 2)
        torus = Torus(major_radius=1, minor_radius=0.3).shift(DOWN * 2)
        dot3d = Dot3D(point=[1, 1, 1], color=RED)
        arrow3d = Arrow3D(start=ORIGIN, end=[1, 1, 1])
        line3d = Line3D(start=[-1, -1, -1], end=[1, 1, 1])
        prism = Prism(dimensions=[1, 2, 0.5]).shift(RIGHT * 3)

        # --- Parametric Surface ---
        surface = Surface(
            lambda u, v: axes.c2p(
                np.cos(u) * np.cos(v),
                np.cos(u) * np.sin(v),
                u,
            ),
            u_range=[-PI, PI],
            v_range=[0, TAU],
            resolution=8,
        )

        self.add(axes, cube, sphere, cone, cylinder, torus, dot3d, arrow3d)


# ═══════════════════════════════════════════════════════════════════════════════
# 32. 3D CAMERA TECHNIQUES
# Source: manim/scene/three_d_scene.py -> ThreeDScene
# Source: manim/camera/three_d_camera.py
# Source: manim/camera/moving_camera.py
# Source: manim/scene/moving_camera_scene.py -> MovingCameraScene
# ═══════════════════════════════════════════════════════════════════════════════

class CameraTechniques3D(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        cube = Cube()
        self.add(axes, cube)

        # --- Set initial camera orientation ---
        self.set_camera_orientation(
            phi=75 * DEGREES,     # polar angle (tilt from top)
            theta=-45 * DEGREES,  # azimuthal angle (rotation around z)
            gamma=0,              # roll angle
        )

        # --- Animate camera movement ---
        self.move_camera(phi=60 * DEGREES, theta=30 * DEGREES, run_time=2)

        # --- Begin ambient rotation ---
        self.begin_ambient_camera_rotation(rate=0.2)  # radians per second
        self.wait(3)
        self.stop_ambient_camera_rotation()

        # --- Zoom (for MovingCameraScene in 2D) ---
        # In MovingCameraScene:
        # self.camera.frame.animate.scale(0.5)  # zoom in
        # self.camera.frame.animate.move_to(target)  # pan


class CameraTechniques2D(MovingCameraScene):
    def construct(self):
        # --- Zoom ---
        sq = Square()
        self.add(sq)
        self.play(self.camera.frame.animate.scale(0.5))  # zoom in 2x
        self.play(self.camera.frame.animate.scale(2))     # zoom out

        # --- Pan ---
        self.play(self.camera.frame.animate.move_to(RIGHT * 3))

        # --- Combined zoom + pan ---
        small_detail = Dot(RIGHT * 5 + UP * 2, color=RED)
        self.add(small_detail)
        self.play(
            self.camera.frame.animate.set(width=4).move_to(small_detail),
            run_time=2,
        )

        # --- Save and restore camera state ---
        self.camera.frame.save_state()
        self.play(self.camera.frame.animate.scale(0.3).move_to(ORIGIN))
        self.play(Restore(self.camera.frame))


# ═══════════════════════════════════════════════════════════════════════════════
# 33. SVG & IMAGE MOBJECTS
# Source: manim/mobject/svg/svg_mobject.py -> SVGMobject
# Source: manim/mobject/types/image_mobject.py -> ImageMobject
# ═══════════════════════════════════════════════════════════════════════════════

class SVGImageExamples(Scene):
    def construct(self):
        # --- SVGMobject ---
        # svg = SVGMobject("path/to/file.svg")
        # svg.scale(2).set_color(BLUE)

        # --- ImageMobject ---
        # img = ImageMobject("path/to/image.png")
        # img.scale(0.5).to_corner(UR)
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 34. VECTOR FIELDS
# Source: manim/mobject/vector_field.py
# Classes: VectorField, ArrowVectorField, StreamLines
# ═══════════════════════════════════════════════════════════════════════════════

class VectorFieldExamples(Scene):
    def construct(self):
        # --- ArrowVectorField ---
        arrow_field = ArrowVectorField(
            lambda pos: np.array([-pos[1], pos[0], 0]),
            x_range=[-4, 4, 0.5],
            y_range=[-3, 3, 0.5],
        )
        self.add(arrow_field)

        # --- StreamLines ---
        stream = StreamLines(
            lambda pos: np.array([np.sin(pos[1]), np.cos(pos[0]), 0]),
            x_range=[-4, 4, 0.3],
            y_range=[-3, 3, 0.3],
            stroke_width=2,
            colors=[BLUE, CYAN, GREEN, YELLOW],
        )
        # Animate creation
        # self.play(stream.create(), run_time=3)

        # Start flowing animation
        # stream.start_animation(warm_up=False, flow_speed=1.5)
        # self.wait(3)
        # stream.end_animation()


# ═══════════════════════════════════════════════════════════════════════════════
# 35. MATRIX MOBJECT
# Source: manim/mobject/matrix.py
# Classes: Matrix, DecimalMatrix, IntegerMatrix, MobjectMatrix
# ═══════════════════════════════════════════════════════════════════════════════

class MatrixExamples(Scene):
    def construct(self):
        m = Matrix([[1, 2], [3, 4]])
        dm = DecimalMatrix([[1.5, 2.7], [3.1, 4.9]], num_decimal_places=1)
        im = IntegerMatrix([[1, 0], [0, 1]])

        # Access elements
        # m.get_entries()
        # m.get_brackets()
        # m.get_rows()
        # m.get_columns()

        VGroup(m, dm, im).arrange(RIGHT, buff=1)
        self.add(m, dm, im)


# ═══════════════════════════════════════════════════════════════════════════════
# 36. BRACE MOBJECT
# Source: manim/mobject/svg/brace.py
# Classes: Brace, BraceLabel, ArcBrace, BraceBetweenPoints
# ═══════════════════════════════════════════════════════════════════════════════

class BraceExamples(Scene):
    def construct(self):
        sq = Square()
        brace_down = Brace(sq, DOWN)
        brace_label = brace_down.get_tex("width")

        brace_right = Brace(sq, RIGHT)
        brace_right_label = brace_right.get_text("height")

        # BraceBetweenPoints
        bbp = BraceBetweenPoints(LEFT * 2, RIGHT * 2, direction=DOWN)

        # ArcBrace
        arc = Arc(radius=2, start_angle=0, angle=PI / 2)
        arc_brace = ArcBrace(arc)

        self.add(sq, brace_down, brace_label, brace_right, brace_right_label)


# ═══════════════════════════════════════════════════════════════════════════════
# 37. BOOLEAN OPS
# Source: manim/mobject/geometry/boolean_ops.py
# Classes: Union, Intersection, Difference, Exclusion
# ═══════════════════════════════════════════════════════════════════════════════

class BooleanOpsExamples(Scene):
    def construct(self):
        a = Circle(radius=1, color=RED, fill_opacity=0.5).shift(LEFT * 0.5)
        b = Circle(radius=1, color=BLUE, fill_opacity=0.5).shift(RIGHT * 0.5)

        union = Union(a, b, color=GREEN, fill_opacity=0.5)
        intersection = Intersection(a, b, color=YELLOW, fill_opacity=0.5)
        difference = Difference(a, b, color=PURPLE, fill_opacity=0.5)
        exclusion = Exclusion(a, b, color=ORANGE, fill_opacity=0.5)

        VGroup(union, intersection, difference, exclusion).arrange(RIGHT, buff=1)
        self.add(*self.mobjects)


# ═══════════════════════════════════════════════════════════════════════════════
# 38. CODE MOBJECT
# Source: manim/mobject/text/code_mobject.py
# Classes: Code
# ═══════════════════════════════════════════════════════════════════════════════

class CodeExamples(Scene):
    def construct(self):
        code = Code(
            code_string='def hello():\n    print("Hello World")',
            language="python",
            formatter_style="monokai",
            background="rectangle",
            font_size=24,
        )
        self.add(code)

        # Access parts
        # code.code  -> the rendered code VGroup
        # code.line_numbers  -> line numbers
        # code.background_mobject  -> the background


# ═══════════════════════════════════════════════════════════════════════════════
# RATE FUNCTIONS REFERENCE
# Source: manim/utils/rate_functions.py
# Available: linear, smooth, rush_into, rush_from,
#            slow_into, double_smooth, there_and_back,
#            there_and_back_with_pause, running_start,
#            wiggle, ease_in_sine, ease_out_sine, ease_in_out_sine,
#            ease_in_quad, ease_out_quad, ease_in_out_quad,
#            ease_in_cubic, ease_out_cubic, ease_in_out_cubic,
#            ease_in_quart, ease_out_quart, ease_in_out_quart,
#            ease_in_quint, ease_out_quint, ease_in_out_quint,
#            ease_in_expo, ease_out_expo, ease_in_out_expo,
#            ease_in_circ, ease_out_circ, ease_in_out_circ,
#            ease_in_back, ease_out_back, ease_in_out_back,
#            ease_in_elastic, ease_out_elastic, ease_in_out_elastic,
#            ease_in_bounce, ease_out_bounce, ease_in_out_bounce,
#            not_quite_there, squish_rate_func
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# COLOR CONSTANTS REFERENCE
# Source: manim/utils/color/manim_colors.py
# ═══════════════════════════════════════════════════════════════════════════════
# WHITE, GRAY/GREY variants (GREY_A through GREY_E, DARK_GREY, LIGHT_GREY)
# BLACK
# PURE_RED, PURE_GREEN, PURE_BLUE
# RED variants: RED_A through RED_E, MAROON_A through MAROON_E
# GREEN variants: GREEN_A through GREEN_E, TEAL_A through TEAL_E
# BLUE variants: BLUE_A through BLUE_E, DARK_BLUE
# YELLOW variants: YELLOW_A through YELLOW_E, GOLD_A through GOLD_E
# PURPLE variants: PURPLE_A through PURPLE_E
# PINK, LIGHT_PINK
# ORANGE
# PURE_YELLOW (very bright yellow, used for Indicate)
# rgb_to_color([r, g, b]) for custom colors
# ManimColor("#hexcode") for hex colors


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTION CONSTANTS REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════
# ORIGIN = [0, 0, 0]
# UP, DOWN, LEFT, RIGHT
# UL (UP+LEFT), UR (UP+RIGHT), DL (DOWN+LEFT), DR (DOWN+RIGHT)
# OUT = [0, 0, 1], IN = [0, 0, -1]
# PI, TAU = 2*PI
# DEGREES = PI/180


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETE ANIMATION CLASS INDEX (alphabetical)
# ═══════════════════════════════════════════════════════════════════════════════
"""
ANIMATION CLASSES:
    AddTextLetterByLetter    - Show text letter by letter
    AddTextWordByWord        - Show text word by word (currently broken)
    AnimatedBoundary         - Animated color-cycling boundary
    AnimationGroup           - Play multiple animations simultaneously
    ApplyComplexFunction     - Apply complex function to mobject
    ApplyFunction            - Apply arbitrary function returning Mobject
    ApplyMatrix              - Apply matrix transform
    ApplyMethod              - Animate a method call (use .animate instead)
    ApplyPointwiseFunction   - Apply function to each point
    ApplyWave                - Wave distortion
    Blink                    - Toggle visibility
    Broadcast                - Expanding rings from focal point
    ChangeDecimalToValue     - Animate decimal to target value
    ChangingDecimal          - Animate decimal by function
    Circumscribe             - Draw temporary surrounding shape
    ClockwiseTransform       - Transform along clockwise arc
    ComplexHomotopy          - Homotopy in complex plane
    CounterclockwiseTransform - Transform along CCW arc
    Create                   - Incrementally draw VMobject
    CyclicReplace            - Cyclic position swap
    DrawBorderThenFill       - Draw border then fill
    FadeIn                   - Fade in (supports shift, scale, target_position)
    FadeOut                  - Fade out (supports shift, scale, target_position)
    FadeToColor              - Animate color change
    FadeTransform            - Cross-fade between mobjects
    FadeTransformPieces      - Cross-fade submobjects piecewise
    Flash                    - Radiating lines from a point
    FocusOn                  - Spotlight shrinking to point
    GrowArrow                - Grow arrow from start
    GrowFromCenter           - Grow from center point
    GrowFromEdge             - Grow from bounding box edge
    GrowFromPoint            - Grow from arbitrary point
    Homotopy                 - (x,y,z,t) -> (x',y',z') transform
    Indicate                 - Temporary scale + recolor
    LaggedStart              - Staggered animation starts
    LaggedStartMap           - Map animation to submobjects with lag
    MaintainPositionRelativeTo - Keep relative position to tracked mob
    MoveAlongPath            - Move mob along VMobject path
    MoveToTarget             - Move to .target attribute
    PhaseFlow                - Flow along vector field
    RemoveTextLetterByLetter - Remove text letter by letter
    ReplacementTransform     - Transform replacing source with target
    Restore                  - Restore to saved state
    Rotate                   - Rotation (Transform-based)
    Rotating                 - Continuous rotation (Animation-based)
    ScaleInPlace             - Scale animation
    ShowIncreasingSubsets    - Show submobjects cumulatively
    ShowPassingFlash         - Sliver traveling along stroke
    ShowSubmobjectsOneByOne  - Show one submobject at a time
    ShrinkToCenter           - Shrink to nothing
    SmoothedVectorizedHomotopy - Smooth homotopy
    SpinInFromNothing        - Spin in while growing
    SpiralIn                 - Spiral flight to final position
    Succession               - Play animations sequentially
    Swap                     - Swap two mobjects (alias for CyclicReplace)
    Transform                - Morph source into target
    TransformFromCopy        - Transform a copy, keep original
    TransformMatchingShapes  - Match by point shape hash
    TransformMatchingTex     - Match by tex_string
    TypeWithCursor           - Type text with cursor
    Uncreate                 - Reverse of Create
    UntypeWithCursor         - Delete text with cursor
    Unwrite                  - Reverse of Write
    UpdateFromAlphaFunc      - Update mob by function of alpha
    UpdateFromFunc           - Update mob by function each frame
    Wiggle                   - Scale + rotate wiggle
    Write                    - Hand-writing simulation

MOBJECT CLASSES:
    Geometry: Arc, ArcBetweenPoints, Circle, Dot, Ellipse, Line,
              DashedLine, Arrow, Vector, DoubleArrow, CurvedArrow,
              Polygon, RegularPolygon, Triangle, Square, Rectangle,
              RoundedRectangle, Star, Annulus, Sector, AnnularSector,
              Angle, RightAngle, Elbow, SurroundingRectangle,
              BackgroundRectangle, Cross, Underline, Cutout, ConvexHull,
              ArcPolygon, LabeledDot, AnnotationDot, TangentLine

    Text:     Text, MarkupText, Tex, MathTex, BulletedList, Title,
              DecimalNumber, Integer, Code, Paragraph

    Graphing: Axes, ThreeDAxes, NumberPlane, PolarPlane, ComplexPlane,
              NumberLine, UnitInterval, BarChart, ParametricFunction,
              ImplicitFunction

    Tables:   Table, MathTable, MobjectTable, IntegerTable, DecimalTable

    3D:       Surface, Sphere, Cube, Prism, Cone, Cylinder, Torus,
              Dot3D, Arrow3D, Line3D, Tetrahedron, Octahedron,
              Icosahedron, Dodecahedron

    Graphs:   Graph, DiGraph

    Other:    Matrix, DecimalMatrix, IntegerMatrix, MobjectMatrix,
              Brace, BraceBetweenPoints, ArcBrace,
              SVGMobject, ImageMobject,
              VGroup, Group, VDict,
              ArrowVectorField, StreamLines,
              ValueTracker, ComplexValueTracker,
              TracedPath, AnimatedBoundary,
              Union, Intersection, Difference, Exclusion
"""
