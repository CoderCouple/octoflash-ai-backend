"""
=============================================================================
COMPLETE MANIM CE ANIMATION, TRANSITION, EFFECT & CAMERA REFERENCE
=============================================================================
Derived from direct source code inspection of every animation module in
the installed Manim CE package. Every class, every parameter, every
variation -- with complete working code for each.

Source files inspected:
  manim/animation/fading.py
  manim/animation/transform.py
  manim/animation/creation.py
  manim/animation/indication.py
  manim/animation/composition.py
  manim/animation/movement.py
  manim/animation/growing.py
  manim/animation/rotation.py
  manim/animation/animation.py
  manim/animation/changing.py
  manim/animation/numbers.py
  manim/animation/specialized.py
  manim/animation/speedmodifier.py
  manim/animation/transform_matching_parts.py
  manim/animation/updaters/update.py
  manim/animation/updaters/mobject_update_utils.py
  manim/camera/moving_camera.py
  manim/scene/moving_camera_scene.py
  manim/scene/zoomed_scene.py
  manim/utils/rate_functions.py
=============================================================================
"""

from manim import *
import numpy as np

# =============================================================================
# SECTION 1: FADE ANIMATIONS (manim/animation/fading.py)
# =============================================================================
# The fading module exports exactly TWO classes: FadeIn and FadeOut.
# Both inherit from _Fade(Transform).
#
# Parameters for both:
#   - *mobjects: one or more Mobject (grouped if multiple)
#   - shift: np.ndarray | None  -- vector the mobject shifts during fade
#   - target_position: np.ndarray | Mobject | None  -- position to/from which it moves
#   - scale: float = 1  -- scale factor during fade
#   - run_time, rate_func, lag_ratio  (standard Animation params)
#
# NOTE: shift and target_position are mutually exclusive concepts.
# If target_position is set and shift is None, shift is computed from target_position.
# If target_position is a Mobject, its center is used.

class Sec01_FadeIn_Basic(Scene):
    """FadeIn with no parameters -- pure opacity fade."""
    def construct(self):
        sq = Square(color=BLUE, fill_opacity=0.5)
        self.play(FadeIn(sq))
        self.wait()


class Sec01_FadeIn_Shift(Scene):
    """FadeIn with shift -- mobject slides in from offset direction."""
    def construct(self):
        # shift=DOWN means the object starts ABOVE and slides DOWN into place
        # (for FadeIn, the shift direction is REVERSED -- it fades in FROM -shift)
        t1 = Text("From below").shift(UP)
        t2 = Text("From above")
        t3 = Text("From left").shift(DOWN)

        self.play(FadeIn(t1, shift=UP))       # starts below, slides up
        self.play(FadeIn(t2, shift=DOWN))      # starts above, slides down
        self.play(FadeIn(t3, shift=RIGHT))     # starts to the left, slides right
        self.wait()


class Sec01_FadeIn_Scale(Scene):
    """FadeIn with scale -- mobject grows/shrinks as it fades in."""
    def construct(self):
        c1 = Circle(color=RED).shift(LEFT * 2)
        c2 = Circle(color=GREEN)
        c3 = Circle(color=BLUE).shift(RIGHT * 2)

        # scale < 1 means object STARTS smaller and grows to normal
        self.play(FadeIn(c1, scale=0.5))
        # scale > 1 means object STARTS larger and shrinks to normal
        self.play(FadeIn(c2, scale=2.0))
        # scale = 1 is the default (no scaling)
        self.play(FadeIn(c3, scale=1.0))
        self.wait()


class Sec01_FadeIn_TargetPosition(Scene):
    """FadeIn with target_position -- fades in from a specific point or mobject."""
    def construct(self):
        dot = Dot(UP * 2 + LEFT * 2, color=YELLOW)
        sq = Square(color=BLUE).shift(DOWN)
        self.add(dot)

        # Fades in from the dot's position
        self.play(FadeIn(sq, target_position=dot))
        self.wait()

        # Can also use a raw point
        tri = Triangle(color=RED).shift(RIGHT * 2)
        self.play(FadeIn(tri, target_position=np.array([-3, -2, 0])))
        self.wait()


class Sec01_FadeIn_ShiftAndScale(Scene):
    """FadeIn combining shift AND scale."""
    def construct(self):
        text = Text("Hello Manim!", font_size=48)
        self.play(FadeIn(text, shift=DOWN * 0.5, scale=0.66))
        self.wait()


class Sec01_FadeIn_MultipleMobjects(Scene):
    """FadeIn with multiple mobjects -- they are auto-grouped."""
    def construct(self):
        s = Square(color=RED).shift(LEFT)
        c = Circle(color=BLUE).shift(RIGHT)
        # Passing multiple mobjects groups them automatically
        self.play(FadeIn(s, c, shift=UP))
        self.wait()


class Sec01_FadeOut_Basic(Scene):
    """FadeOut with no parameters -- pure opacity fade."""
    def construct(self):
        sq = Square(color=BLUE, fill_opacity=0.5)
        self.add(sq)
        self.play(FadeOut(sq))
        self.wait()


class Sec01_FadeOut_Shift(Scene):
    """FadeOut with shift -- mobject slides out in the shift direction."""
    def construct(self):
        t = Text("Goodbye!")
        self.add(t)
        # shift=DOWN means the object moves DOWN as it fades out
        self.play(FadeOut(t, shift=DOWN * 2))
        self.wait()


class Sec01_FadeOut_Scale(Scene):
    """FadeOut with scale -- mobject shrinks/grows as it fades out."""
    def construct(self):
        sq = Square(color=RED, fill_opacity=0.5)
        self.add(sq)
        # scale < 1: object shrinks while fading out
        self.play(FadeOut(sq, scale=0.5))
        self.wait()


class Sec01_FadeOut_TargetPosition(Scene):
    """FadeOut with target_position -- fades out toward a specific point."""
    def construct(self):
        dot = Dot(UP * 2 + RIGHT * 3, color=YELLOW)
        sq = Square(color=GREEN)
        self.add(dot, sq)
        # Fades out toward the dot
        self.play(FadeOut(sq, target_position=dot))
        self.wait()


class Sec01_FadeOut_ShiftAndScale(Scene):
    """FadeOut combining shift AND scale."""
    def construct(self):
        text = Text("Vanishing!", font_size=48)
        self.add(text)
        self.play(FadeOut(text, shift=DOWN * 2, scale=1.5))
        self.wait()


# =============================================================================
# SECTION 2: TRANSFORM ANIMATIONS (manim/animation/transform.py)
# =============================================================================
# Full list of exported classes:
#   Transform, ReplacementTransform, TransformFromCopy,
#   ClockwiseTransform, CounterclockwiseTransform,
#   MoveToTarget, ApplyMethod, ApplyPointwiseFunction,
#   ApplyPointwiseFunctionToCenter, FadeToColor, FadeTransform,
#   FadeTransformPieces, ScaleInPlace, ShrinkToCenter, Restore,
#   ApplyFunction, ApplyMatrix, ApplyComplexFunction,
#   CyclicReplace, Swap, TransformAnimations

class Sec02_Transform_Basic(Scene):
    """Transform -- morphs mobject into target. Original stays in scene (mutated)."""
    def construct(self):
        sq = Square(color=BLUE)
        ci = Circle(color=RED)
        self.add(sq)
        # After Transform, 'sq' is mutated to look like 'ci', but 'ci' is NOT in scene
        self.play(Transform(sq, ci))
        self.wait()


class Sec02_Transform_PathArc(Scene):
    """Transform with path_arc -- points follow a circular arc."""
    def construct(self):
        sq = Square(color=BLUE).shift(LEFT * 2)
        ci = Circle(color=RED).shift(RIGHT * 2)
        self.add(sq)
        # path_arc in radians. Positive = counterclockwise.
        self.play(Transform(sq, ci, path_arc=PI / 2))
        self.wait()


class Sec02_Transform_PathArcAxis(Scene):
    """Transform with path_arc_axis -- 3D arc axis."""
    def construct(self):
        sq = Square(color=BLUE).shift(LEFT * 2)
        ci = Circle(color=RED).shift(RIGHT * 2)
        self.add(sq)
        self.play(Transform(sq, ci, path_arc=PI, path_arc_axis=UP))
        self.wait()


class Sec02_ReplacementTransform(Scene):
    """ReplacementTransform -- source is REMOVED, target is ADDED to scene."""
    def construct(self):
        sq = Square(color=BLUE)
        ci = Circle(color=RED)
        self.add(sq)
        # After this, 'sq' is removed from scene and 'ci' is added
        self.play(ReplacementTransform(sq, ci))
        # Now ci is the mobject in the scene
        self.play(ci.animate.shift(UP))
        self.wait()


class Sec02_TransformFromCopy(Scene):
    """TransformFromCopy -- preserves original, transforms a COPY into target."""
    def construct(self):
        sq = Square(color=BLUE).shift(LEFT * 2)
        ci = Circle(color=RED).shift(RIGHT * 2)
        self.add(sq)
        # sq remains unchanged; a copy morphs into ci
        self.play(TransformFromCopy(sq, ci))
        self.wait()


class Sec02_ClockwiseTransform(Scene):
    """ClockwiseTransform -- points follow a clockwise arc (path_arc=-PI)."""
    def construct(self):
        d1 = Dot(LEFT * 2, color=BLUE)
        d2 = Dot(RIGHT * 2, color=RED)
        self.add(d1)
        self.play(ClockwiseTransform(d1, d2))
        self.wait()


class Sec02_CounterclockwiseTransform(Scene):
    """CounterclockwiseTransform -- points follow CCW arc (path_arc=PI)."""
    def construct(self):
        d1 = Dot(LEFT * 2, color=BLUE)
        d2 = Dot(RIGHT * 2, color=RED)
        self.add(d1)
        self.play(CounterclockwiseTransform(d1, d2))
        self.wait()


class Sec02_MoveToTarget(Scene):
    """MoveToTarget -- animates mobject to its .target attribute."""
    def construct(self):
        c = Circle(color=BLUE)
        self.add(c)

        c.generate_target()
        c.target.set_fill(GREEN, opacity=0.5)
        c.target.shift(2 * RIGHT + UP)
        c.target.scale(0.5)

        self.play(MoveToTarget(c))
        self.wait()


class Sec02_DotAnimate(Scene):
    """The .animate syntax -- syntactic sugar for MoveToTarget."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        # sq.animate creates a target from chained method calls
        self.play(sq.animate.shift(RIGHT * 2).set_color(RED).scale(0.5))
        self.wait()


class Sec02_ApplyMethod(Scene):
    """ApplyMethod -- pass a bound method to animate."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        # Equivalent to sq.animate.set_color(RED)
        self.play(ApplyMethod(sq.set_color, RED))
        self.wait()


class Sec02_ApplyFunction(Scene):
    """ApplyFunction -- apply an arbitrary function that returns a Mobject."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)

        def my_transform(mob):
            mob.scale(2)
            mob.set_color(RED)
            mob.rotate(PI / 4)
            return mob

        self.play(ApplyFunction(my_transform, sq))
        self.wait()


class Sec02_ApplyPointwiseFunction(Scene):
    """ApplyPointwiseFunction -- apply a function to each point of the mobject."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        # Exponential conformal map
        self.play(
            ApplyPointwiseFunction(
                lambda point: complex_to_R3(np.exp(R3_to_complex(point))),
                sq
            )
        )
        self.wait()


class Sec02_ApplyMatrix(Scene):
    """ApplyMatrix -- apply a matrix transformation."""
    def construct(self):
        sq = Square(color=BLUE)
        plane = NumberPlane()
        self.add(plane, sq)
        matrix = [[1, 1], [0, 2 / 3]]
        self.play(ApplyMatrix(matrix, sq))
        self.wait()


class Sec02_ApplyComplexFunction(Scene):
    """ApplyComplexFunction -- apply a complex-valued function."""
    def construct(self):
        plane = NumberPlane()
        self.add(plane)
        self.play(ApplyComplexFunction(lambda z: z**2, plane), run_time=3)
        self.wait()


class Sec02_FadeToColor(Scene):
    """FadeToColor -- animate color change."""
    def construct(self):
        text = Text("Hello!")
        self.add(text)
        self.play(FadeToColor(text, RED))
        self.wait()


class Sec02_ScaleInPlace(Scene):
    """ScaleInPlace -- animate scaling about center."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(ScaleInPlace(sq, 2))
        self.wait()


class Sec02_ShrinkToCenter(Scene):
    """ShrinkToCenter -- shrink to zero at center (remover)."""
    def construct(self):
        text = Text("Shrinking!")
        self.add(text)
        self.play(ShrinkToCenter(text))
        self.wait()


class Sec02_Restore(Scene):
    """Restore -- return to last saved state."""
    def construct(self):
        sq = Square(color=BLUE)
        sq.save_state()
        self.add(sq)
        self.play(sq.animate.set_color(PURPLE).set_opacity(0.5).shift(2 * LEFT).scale(3))
        self.play(sq.animate.shift(5 * DOWN).rotate(PI / 4))
        self.wait()
        self.play(Restore(sq), run_time=2)
        self.wait()


class Sec02_FadeTransform(Scene):
    """FadeTransform -- cross-fade one mobject into another.
    Parameters: stretch=True, dim_to_match=1"""
    def construct(self):
        rect = Rectangle(width=4, height=1, color=BLUE)
        circ = Circle(fill_opacity=1, color=RED).scale(0.5)
        self.add(rect)
        self.play(FadeTransform(rect, circ))
        self.wait()


class Sec02_FadeTransform_Params(Scene):
    """FadeTransform with stretch=False and dim_to_match."""
    def construct(self):
        r1 = Rectangle(width=4, height=1, color=BLUE).shift(UP)
        r2 = Rectangle(width=4, height=1, color=GREEN).shift(DOWN)
        c1 = Circle(fill_opacity=1, color=RED).scale(0.25).shift(UP)
        c2 = Circle(fill_opacity=1, color=YELLOW).scale(0.25).shift(DOWN)
        self.add(r1, r2)
        self.play(
            FadeTransform(r1, c1, stretch=False, dim_to_match=0),  # match x-dimension
            FadeTransform(r2, c2, stretch=False, dim_to_match=1),  # match y-dimension
        )
        self.wait()


class Sec02_FadeTransformPieces(Scene):
    """FadeTransformPieces -- cross-fade submobjects individually."""
    def construct(self):
        src = VGroup(Square(color=BLUE), Circle(color=RED).shift(RIGHT))
        target = VGroup(Circle(color=GREEN), Triangle(color=YELLOW).shift(RIGHT))
        self.add(src)
        self.play(FadeTransformPieces(src, target))
        self.wait()


class Sec02_CyclicReplace(Scene):
    """CyclicReplace -- mobjects swap positions cyclically."""
    def construct(self):
        group = VGroup(
            Square(color=RED),
            Circle(color=GREEN),
            Triangle(color=BLUE),
            Star(color=YELLOW)
        ).arrange(RIGHT, buff=1)
        self.add(group)
        for _ in range(4):
            self.play(CyclicReplace(*group))


class Sec02_Swap(Scene):
    """Swap -- CyclicReplace with exactly two mobjects."""
    def construct(self):
        a = Square(color=RED).shift(LEFT * 2)
        b = Circle(color=BLUE).shift(RIGHT * 2)
        self.add(a, b)
        self.play(Swap(a, b))
        self.wait()


# =============================================================================
# SECTION 2b: TRANSFORM MATCHING PARTS (manim/animation/transform_matching_parts.py)
# =============================================================================
# TransformMatchingShapes -- matches by point hash
# TransformMatchingTex -- matches by tex_string

class Sec02b_TransformMatchingShapes(Scene):
    """TransformMatchingShapes -- anagram effect, matching shapes by point hash."""
    def construct(self):
        src = Text("the morse code")
        tar = Text("here come dots")
        self.play(Write(src))
        self.wait(0.5)
        self.play(TransformMatchingShapes(src, tar, path_arc=PI / 2))
        self.wait()


class Sec02b_TransformMatchingTex(Scene):
    """TransformMatchingTex -- matching LaTeX parts by tex_string.
    Use double braces {{...}} to define matchable parts."""
    def construct(self):
        eq1 = MathTex("{{x}}^2", "+", "{{y}}^2", "=", "{{z}}^2")
        eq2 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")
        eq3 = MathTex("{{a}}^2", "=", "{{c}}^2", "-", "{{b}}^2")

        self.add(eq1)
        self.wait(0.5)
        self.play(TransformMatchingTex(eq1, eq2))
        self.wait(0.5)
        self.play(TransformMatchingTex(eq2, eq3))
        self.wait()


class Sec02b_TransformMatchingTex_KeyMap(Scene):
    """TransformMatchingTex with key_map to manually map mismatched keys."""
    def construct(self):
        eq1 = MathTex("{{x}}^2", "+", "{{y}}^2", "=", "{{z}}^2")
        eq2 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")
        self.add(eq1)
        # key_map: x -> a, y -> b, z -> c
        self.play(TransformMatchingTex(
            eq1, eq2,
            key_map={"x": "a", "y": "b", "z": "c"}
        ))
        self.wait()


class Sec02b_TransformMatchingTex_FadeMismatches(Scene):
    """TransformMatchingTex with fade_transform_mismatches=True."""
    def construct(self):
        eq1 = MathTex("a", "+", "b", "=", "c")
        eq2 = MathTex("a", "\\cdot", "b", "=", "d")
        self.add(eq1)
        self.play(TransformMatchingTex(eq1, eq2, fade_transform_mismatches=True))
        self.wait()


# =============================================================================
# SECTION 3: CREATION ANIMATIONS (manim/animation/creation.py)
# =============================================================================
# Exported: Create, Uncreate, DrawBorderThenFill, Write, Unwrite,
#           ShowPartial (abstract), ShowIncreasingSubsets, SpiralIn,
#           AddTextLetterByLetter, RemoveTextLetterByLetter,
#           ShowSubmobjectsOneByOne, AddTextWordByWord,
#           TypeWithCursor, UntypeWithCursor

class Sec03_Create(Scene):
    """Create -- incrementally draw a VMobject's stroke.
    Parameters: lag_ratio=1.0 (applied to submobjects)."""
    def construct(self):
        sq = Square(color=BLUE)
        self.play(Create(sq))
        self.wait()


class Sec03_Create_LagRatio(Scene):
    """Create with different lag_ratio values."""
    def construct(self):
        # lag_ratio=1 (default): submobjects draw one after another
        g1 = VGroup(*[Circle(color=BLUE) for _ in range(5)]).arrange(RIGHT).shift(UP)
        # lag_ratio=0: all submobjects draw simultaneously
        g2 = VGroup(*[Circle(color=RED) for _ in range(5)]).arrange(RIGHT).shift(DOWN)

        self.play(Create(g1, lag_ratio=1))
        self.play(Create(g2, lag_ratio=0))
        self.wait()


class Sec03_Uncreate(Scene):
    """Uncreate -- reverse of Create. Removes stroke progressively."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(Uncreate(sq))
        self.wait()


class Sec03_DrawBorderThenFill(Scene):
    """DrawBorderThenFill -- first draws outline, then fills.
    Parameters: stroke_width=2, stroke_color=None, rate_func=double_smooth."""
    def construct(self):
        sq = Square(fill_opacity=1, fill_color=ORANGE, color=WHITE)
        self.play(DrawBorderThenFill(sq))
        self.wait()


class Sec03_DrawBorderThenFill_CustomStroke(Scene):
    """DrawBorderThenFill with custom stroke color and width."""
    def construct(self):
        sq = Square(fill_opacity=1, fill_color=BLUE)
        self.play(DrawBorderThenFill(sq, stroke_width=5, stroke_color=YELLOW))
        self.wait()


class Sec03_Write(Scene):
    """Write -- hand-writing effect for Text/Tex.
    Inherits DrawBorderThenFill. Parameters: rate_func=linear, reverse=False.
    Auto-calculates run_time and lag_ratio from text length."""
    def construct(self):
        text = Text("Hello, Manim!", font_size=72)
        self.play(Write(text))
        self.wait()


class Sec03_Write_Reversed(Scene):
    """Write with reverse=True -- erases from end to start."""
    def construct(self):
        text = Text("Reversed!", font_size=72)
        self.add(text)
        self.play(Write(text, reverse=True, remover=True))
        self.wait()


class Sec03_Unwrite(Scene):
    """Unwrite -- erasing effect. Parameters: reverse=True by default."""
    def construct(self):
        text = Tex("Alice and Bob").scale(3)
        self.add(text)
        self.play(Unwrite(text))
        self.wait()


class Sec03_Unwrite_NotReversed(Scene):
    """Unwrite with reverse=False -- erases in forward order."""
    def construct(self):
        text = Tex("Alice and Bob").scale(3)
        self.add(text)
        self.play(Unwrite(text, reverse=False))
        self.wait()


class Sec03_ShowIncreasingSubsets(Scene):
    """ShowIncreasingSubsets -- show submobjects one at a time, cumulative."""
    def construct(self):
        dots = VGroup(*[
            Dot(color=random_color()).shift(RIGHT * i * 0.5)
            for i in range(10)
        ]).center()
        self.add(dots)
        self.play(ShowIncreasingSubsets(dots), run_time=3)
        self.wait()


class Sec03_ShowSubmobjectsOneByOne(Scene):
    """ShowSubmobjectsOneByOne -- show one at a time, hiding previous."""
    def construct(self):
        texts = VGroup(*[
            Text(f"Slide {i+1}", font_size=48)
            for i in range(5)
        ])
        self.play(ShowSubmobjectsOneByOne(texts), run_time=5)
        self.wait()


class Sec03_AddTextLetterByLetter(Scene):
    """AddTextLetterByLetter -- typewriter effect.
    Parameters: time_per_char=0.1. Only for Text, not MathTex."""
    def construct(self):
        text = Text("Typing effect...", font_size=48)
        self.play(AddTextLetterByLetter(text, time_per_char=0.05))
        self.wait()


class Sec03_RemoveTextLetterByLetter(Scene):
    """RemoveTextLetterByLetter -- reverse typewriter."""
    def construct(self):
        text = Text("Disappearing...", font_size=48)
        self.add(text)
        self.play(RemoveTextLetterByLetter(text, time_per_char=0.05))
        self.wait()


class Sec03_TypeWithCursor(Scene):
    """TypeWithCursor -- typewriter with visible cursor.
    Parameters: cursor, buff=0.1, keep_cursor_y=True, leave_cursor_on=True."""
    def construct(self):
        text = Text("Inserting", color=PURPLE).scale(1.5)
        cursor = Rectangle(
            color=GREY_A, fill_color=GREY_A, fill_opacity=1.0,
            height=1.1, width=0.1,
        ).move_to(text[0])
        self.play(TypeWithCursor(text, cursor))
        self.play(Blink(cursor, blinks=2))
        self.wait()


class Sec03_UntypeWithCursor(Scene):
    """UntypeWithCursor -- reverse typing with cursor."""
    def construct(self):
        text = Text("Deleting", color=PURPLE).scale(1.5)
        cursor = Rectangle(
            color=GREY_A, fill_color=GREY_A, fill_opacity=1.0,
            height=1.1, width=0.1,
        ).move_to(text[-1])
        self.add(text)
        self.play(UntypeWithCursor(text, cursor))
        self.wait()


class Sec03_SpiralIn(Scene):
    """SpiralIn -- submobjects fly in on spiral trajectories.
    Parameters: scale_factor=8, fade_in_fraction=0.3."""
    def construct(self):
        pi = MathTex(r"\pi").scale(7).shift(2.25 * LEFT + 1.5 * UP)
        circle = Circle(color=GREEN, fill_opacity=1).shift(LEFT)
        square = Square(color=BLUE, fill_opacity=1).shift(UP)
        shapes = VGroup(pi, circle, square)
        self.play(SpiralIn(shapes))
        self.wait()


# =============================================================================
# SECTION 4: INDICATION ANIMATIONS (manim/animation/indication.py)
# =============================================================================
# Exported: FocusOn, Indicate, Flash, ShowPassingFlash,
#           ShowPassingFlashWithThinningStrokeWidth, ApplyWave,
#           Circumscribe, Wiggle, Blink

class Sec04_FocusOn(Scene):
    """FocusOn -- spotlight shrinks to a point.
    Parameters: opacity=0.2, color=GREY, run_time=2."""
    def construct(self):
        dot = Dot(color=YELLOW).shift(DOWN)
        self.add(Tex("Focus below:"), dot)
        self.play(FocusOn(dot))
        self.wait()


class Sec04_FocusOn_CustomColor(Scene):
    """FocusOn with custom opacity and color."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(FocusOn(sq, opacity=0.5, color=RED, run_time=1.5))
        self.wait()


class Sec04_Indicate(Scene):
    """Indicate -- temporarily scale and recolor.
    Parameters: scale_factor=1.2, color=PURE_YELLOW, rate_func=there_and_back."""
    def construct(self):
        tex = Tex("Indicate").scale(3)
        self.add(tex)
        self.play(Indicate(tex))
        self.wait()


class Sec04_Indicate_Custom(Scene):
    """Indicate with custom scale_factor and color."""
    def construct(self):
        tex = Tex("Custom Indicate").scale(2)
        self.add(tex)
        self.play(Indicate(tex, scale_factor=1.5, color=RED))
        self.wait()


class Sec04_Flash(Scene):
    """Flash -- radial lines burst from a point.
    Parameters: line_length=0.2, num_lines=12, flash_radius=0.1,
                line_stroke_width=3, color=PURE_YELLOW, time_width=1, run_time=1."""
    def construct(self):
        dot = Dot(color=YELLOW).shift(DOWN)
        self.add(dot)
        self.play(Flash(dot))
        self.wait()


class Sec04_Flash_CustomParams(Scene):
    """Flash with all custom parameters."""
    def construct(self):
        circle = Circle(radius=2, color=BLUE)
        self.add(circle)
        self.play(Flash(
            circle,
            line_length=1,
            num_lines=30,
            color=RED,
            flash_radius=2 + SMALL_BUFF,
            time_width=0.3,
            run_time=2,
            rate_func=rush_from,
        ))
        self.wait()


class Sec04_ShowPassingFlash(Scene):
    """ShowPassingFlash -- a sliver of stroke travels along the path.
    Parameters: time_width=0.1 (fraction of the path visible at once)."""
    def construct(self):
        p = RegularPolygon(5, color=DARK_GRAY, stroke_width=6).scale(3)
        self.add(p)
        for tw in [0.2, 0.5, 1, 2]:
            self.play(ShowPassingFlash(
                p.copy().set_color(BLUE),
                run_time=2,
                time_width=tw,
            ))
        self.wait()


class Sec04_ShowPassingFlashWithThinningStrokeWidth(Scene):
    """ShowPassingFlashWithThinningStrokeWidth -- multiple layers with decreasing stroke."""
    def construct(self):
        circle = Circle(color=BLUE, stroke_width=6).scale(2)
        self.add(circle.copy().set_color(DARK_GRAY))
        self.play(ShowPassingFlashWithThinningStrokeWidth(
            circle,
            n_segments=10,
            time_width=0.5,
            run_time=2,
        ))
        self.wait()


class Sec04_ApplyWave(Scene):
    """ApplyWave -- send a wave distortion through the mobject.
    Parameters: direction=UP, amplitude=0.2, wave_func=smooth,
                time_width=1, ripples=1, run_time=2."""
    def construct(self):
        tex = Tex("WaveWaveWave").scale(2)
        self.add(tex)
        # Default wave
        self.play(ApplyWave(tex))
        # Horizontal wave with custom params
        self.play(ApplyWave(tex, direction=RIGHT, time_width=0.5, amplitude=0.3))
        # Multiple ripples
        self.play(ApplyWave(tex, rate_func=linear, ripples=4))
        self.wait()


class Sec04_Wiggle(Scene):
    """Wiggle -- scale and rotate back and forth.
    Parameters: scale_value=1.1, rotation_angle=0.01*TAU, n_wiggles=6,
                scale_about_point=None, rotate_about_point=None, run_time=2."""
    def construct(self):
        tex = Tex("Wiggle").scale(3)
        self.add(tex)
        self.play(Wiggle(tex))
        self.wait()


class Sec04_Wiggle_Custom(Scene):
    """Wiggle with custom parameters."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(Wiggle(
            sq,
            scale_value=1.3,
            rotation_angle=0.05 * TAU,
            n_wiggles=10,
            run_time=3,
        ))
        self.wait()


class Sec04_Circumscribe(Scene):
    """Circumscribe -- draw a temporary shape around a mobject.
    Parameters: shape=Rectangle|Circle, fade_in=False, fade_out=False,
                time_width=0.3, buff=SMALL_BUFF, color=PURE_YELLOW,
                run_time=1, stroke_width=DEFAULT_STROKE_WIDTH."""
    def construct(self):
        lbl = Tex(r"Circum-\\scribe").scale(2)
        self.add(lbl)
        # Default: ShowPassingFlash rectangle
        self.play(Circumscribe(lbl))
        # Circle shape
        self.play(Circumscribe(lbl, Circle))
        # Fade out instead of undraw
        self.play(Circumscribe(lbl, fade_out=True))
        # Wider time_width for longer visible trace
        self.play(Circumscribe(lbl, time_width=2))
        # Fade in AND circle
        self.play(Circumscribe(lbl, Circle, True))
        self.wait()


class Sec04_Blink(Scene):
    """Blink -- toggle visibility on/off.
    Parameters: time_on=0.5, time_off=0.5, blinks=1, hide_at_end=False."""
    def construct(self):
        text = Text("Blinking").scale(1.5)
        self.add(text)
        self.play(Blink(text, blinks=3))
        self.wait()


class Sec04_Blink_HideAtEnd(Scene):
    """Blink with hide_at_end=True."""
    def construct(self):
        text = Text("Vanish after blink").scale(1.5)
        self.add(text)
        self.play(Blink(text, blinks=2, hide_at_end=True))
        self.wait()


# =============================================================================
# SECTION 5: COMPOSITION -- Succession AND AnimationGroup
# (manim/animation/composition.py)
# =============================================================================

class Sec05_AnimationGroup_Simultaneous(Scene):
    """AnimationGroup with lag_ratio=0 (default) -- all play simultaneously."""
    def construct(self):
        sq = Square(color=RED).shift(LEFT * 2)
        ci = Circle(color=BLUE).shift(RIGHT * 2)
        self.add(sq, ci)
        self.play(AnimationGroup(
            sq.animate.shift(RIGHT * 4),
            ci.animate.shift(LEFT * 4),
            lag_ratio=0,  # default: simultaneous
        ))
        self.wait()


class Sec05_AnimationGroup_LagRatio(Scene):
    """AnimationGroup with lag_ratio > 0 -- stagger the start times."""
    def construct(self):
        dots = VGroup(*[Dot() for _ in range(5)]).arrange(DOWN, buff=0.5).shift(LEFT * 3)
        self.add(dots)

        # lag_ratio=0.5: each animation starts at 50% of the previous
        self.play(AnimationGroup(
            *[d.animate.shift(RIGHT * 6) for d in dots],
            lag_ratio=0.5,
            run_time=3,
        ))
        self.wait()


class Sec05_Succession(Scene):
    """Succession -- plays animations one after another (lag_ratio=1)."""
    def construct(self):
        dot1 = Dot(LEFT * 2 + UP * 2, color=BLUE)
        dot2 = Dot(LEFT * 2 + DOWN * 2, color=MAROON)
        dot3 = Dot(RIGHT * 2 + DOWN * 2, color=GREEN)
        dot4 = Dot(RIGHT * 2 + UP * 2, color=YELLOW)
        self.add(dot1, dot2, dot3, dot4)

        self.play(Succession(
            dot1.animate.move_to(dot2),
            dot2.animate.move_to(dot3),
            dot3.animate.move_to(dot4),
            dot4.animate.move_to(dot1),
        ))
        self.wait()


class Sec05_Succession_WithWait(Scene):
    """Succession with Wait and Add mixed in."""
    def construct(self):
        t1 = Text("Step 1", font_size=48)
        t2 = Text("Step 2", font_size=48)
        t3 = Text("Step 3", font_size=48)

        self.play(Succession(
            FadeIn(t1),
            Wait(0.5),
            FadeOut(t1),
            FadeIn(t2),
            Wait(0.5),
            FadeOut(t2),
            FadeIn(t3),
        ))
        self.wait()


# =============================================================================
# SECTION 6: LAGGED START AND LAGGED START MAP
# (manim/animation/composition.py)
# =============================================================================
# DEFAULT_LAGGED_START_LAG_RATIO = 0.05

class Sec06_LaggedStart_Basic(Scene):
    """LaggedStart -- AnimationGroup with default lag_ratio=0.05."""
    def construct(self):
        dots = VGroup(*[Dot() for _ in range(10)]).arrange(RIGHT).shift(UP)
        self.add(dots)
        self.play(LaggedStart(
            *[d.animate.shift(DOWN * 2) for d in dots],
            lag_ratio=0.1,
            run_time=3,
        ))
        self.wait()


class Sec06_LaggedStart_FadeIn(Scene):
    """LaggedStart with FadeIn for staggered appearance."""
    def construct(self):
        squares = VGroup(*[
            Square(color=color, fill_opacity=0.5)
            for color in [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE]
        ]).arrange(RIGHT, buff=0.3)
        self.play(LaggedStart(
            *[FadeIn(s, shift=UP) for s in squares],
            lag_ratio=0.15,
            run_time=2,
        ))
        self.wait()


class Sec06_LaggedStart_HighLagRatio(Scene):
    """LaggedStart with high lag_ratio -- nearly sequential."""
    def construct(self):
        circles = VGroup(*[
            Circle(radius=0.3, color=BLUE, fill_opacity=0.5)
            for _ in range(8)
        ]).arrange(RIGHT)
        self.play(LaggedStart(
            *[GrowFromCenter(c) for c in circles],
            lag_ratio=0.5,  # each starts at 50% of previous
            run_time=4,
        ))
        self.wait()


class Sec06_LaggedStartMap_Basic(Scene):
    """LaggedStartMap -- apply an animation class to each submobject.
    Parameters: animation_class, mobject, arg_creator=None, run_time=2, lag_ratio=0.05."""
    def construct(self):
        dots = VGroup(*[Dot(radius=0.16) for _ in range(35)]).arrange_in_grid(rows=5, cols=7, buff=MED_LARGE_BUFF)
        self.play(LaggedStartMap(FadeIn, dots, lag_ratio=0.1))
        self.wait()


class Sec06_LaggedStartMap_WithCreate(Scene):
    """LaggedStartMap with Create animation."""
    def construct(self):
        circles = VGroup(*[
            Circle(radius=0.3, color=random_color())
            for _ in range(20)
        ]).arrange_in_grid(rows=4, cols=5, buff=0.5)
        self.play(LaggedStartMap(Create, circles, lag_ratio=0.1, run_time=3))
        self.wait()


class Sec06_LaggedStartMap_ArgCreator(Scene):
    """LaggedStartMap with arg_creator to pass arguments."""
    def construct(self):
        dots = VGroup(*[Dot(radius=0.16) for _ in range(35)]).arrange_in_grid(
            rows=5, cols=7, buff=MED_LARGE_BUFF
        )
        self.add(dots)
        # arg_creator returns the args for the animation class
        self.play(LaggedStartMap(
            ApplyMethod, dots,
            lambda m: (m.set_color, YELLOW),
            lag_ratio=0.1,
            rate_func=there_and_back,
            run_time=2,
        ))
        self.wait()


class Sec06_LaggedStartMap_GrowFromCenter(Scene):
    """LaggedStartMap with GrowFromCenter for grid intro."""
    def construct(self):
        grid = VGroup(*[
            Square(side_length=0.5, color=BLUE, fill_opacity=0.3)
            for _ in range(25)
        ]).arrange_in_grid(rows=5, cols=5, buff=0.2)
        self.play(LaggedStartMap(GrowFromCenter, grid, lag_ratio=0.05, run_time=2))
        self.wait()


class Sec06_LaggedStartMap_Write(Scene):
    """LaggedStartMap with Write for staggered text."""
    def construct(self):
        texts = VGroup(*[
            Text(f"Line {i+1}", font_size=36)
            for i in range(5)
        ]).arrange(DOWN, buff=0.3)
        self.play(LaggedStartMap(Write, texts, lag_ratio=0.3, run_time=3))
        self.wait()


class Sec06_LaggedStartMap_FadeOut(Scene):
    """LaggedStartMap with FadeOut for staggered dismissal."""
    def construct(self):
        items = VGroup(*[
            Square(side_length=0.6, color=c, fill_opacity=0.5)
            for c in [RED, ORANGE, YELLOW, GREEN, BLUE]
        ]).arrange(RIGHT, buff=0.3)
        self.add(items)
        self.play(LaggedStartMap(FadeOut, items, shift=DOWN, lag_ratio=0.2))
        self.wait()


# =============================================================================
# SECTION 7: CAMERA -- MovingCameraScene AND ZoomedScene
# (manim/scene/moving_camera_scene.py, manim/scene/zoomed_scene.py)
# =============================================================================

class Sec07_MovingCamera_Pan(MovingCameraScene):
    """MovingCameraScene -- pan the camera to different mobjects."""
    def construct(self):
        s = Square(color=RED, fill_opacity=0.5).move_to(2 * LEFT)
        t = Triangle(color=GREEN, fill_opacity=0.5).move_to(2 * RIGHT)
        self.add(s, t)
        self.play(self.camera.frame.animate.move_to(s))
        self.wait(0.3)
        self.play(self.camera.frame.animate.move_to(t))
        self.wait()


class Sec07_MovingCamera_Zoom(MovingCameraScene):
    """MovingCameraScene -- zoom in and out by changing frame width/height."""
    def construct(self):
        text = Text("Hello World", color=BLUE)
        self.add(text)
        self.camera.frame.save_state()
        # Zoom in: reduce frame width
        self.play(self.camera.frame.animate.set(width=text.width * 1.2))
        self.wait(0.3)
        # Zoom back out: restore
        self.play(Restore(self.camera.frame))
        self.wait()


class Sec07_MovingCamera_ZoomAndPan(MovingCameraScene):
    """MovingCameraScene -- combined zoom + pan."""
    def construct(self):
        s = Square(color=BLUE, fill_opacity=0.5).move_to(2 * LEFT)
        t = Triangle(color=YELLOW, fill_opacity=0.5).move_to(2 * RIGHT)
        self.add(s, t)
        # Zoom into square
        self.play(self.camera.frame.animate.move_to(s).set(width=s.width * 2))
        self.wait(0.3)
        # Pan and zoom to triangle
        self.play(self.camera.frame.animate.move_to(t).set(width=t.width * 2))
        self.wait(0.3)
        # Zoom out to see everything
        self.play(self.camera.frame.animate.move_to(ORIGIN).set(width=14))
        self.wait()


class Sec07_MovingCamera_Scale(MovingCameraScene):
    """MovingCameraScene -- zoom using .scale() on the frame."""
    def construct(self):
        ax = Axes(x_range=[-1, 10], y_range=[-1, 10])
        graph = ax.plot(lambda x: np.sin(x), color=WHITE, x_range=[0, 3 * PI])
        dot_start = Dot(ax.i2gp(graph.t_min, graph))
        dot_end = Dot(ax.i2gp(graph.t_max, graph))
        self.add(ax, graph, dot_start, dot_end)

        self.camera.frame.save_state()
        self.play(self.camera.frame.animate.scale(0.5).move_to(dot_start))
        self.play(self.camera.frame.animate.move_to(dot_end))
        self.play(Restore(self.camera.frame))
        self.wait()


class Sec07_MovingCamera_AutoZoom(MovingCameraScene):
    """MovingCameraScene -- auto_zoom to fit mobjects."""
    def construct(self):
        def create_scene(number):
            frame = Rectangle(width=16, height=9)
            circ = Circle().shift(LEFT)
            text = Tex(f"Scene {number}").next_to(circ, RIGHT)
            frame.add(circ, text)
            return frame

        group = VGroup(*(create_scene(i) for i in range(4))).arrange_in_grid(buff=4)
        self.add(group)
        self.camera.auto_zoom(group[0], animate=False)

        for scene in group:
            self.play(self.camera.auto_zoom(scene))
            self.wait(0.5)
        self.play(self.camera.auto_zoom(group, margin=2))
        self.wait()


class Sec07_ZoomedScene_Basic(ZoomedScene):
    """ZoomedScene -- picture-in-picture zoom display.
    Constructor params: zoom_factor=0.15, zoomed_display_height=3,
                        zoomed_display_width=3, zoomed_display_corner=UP+RIGHT,
                        image_frame_stroke_width=3, zoomed_camera_config={}."""
    def construct(self):
        dot = Dot(color=GREEN)
        self.add(dot)
        self.wait(0.5)
        self.activate_zooming(animate=False)
        self.wait(0.5)
        self.play(dot.animate.shift(LEFT))
        self.wait()


class Sec07_ZoomedScene_Animated(ZoomedScene):
    """ZoomedScene with animated zoom activation."""
    def construct(self):
        dot = Dot(color=GREEN)
        self.add(dot)
        # animate=True calls get_zoom_in_animation + get_zoomed_display_pop_out_animation
        self.activate_zooming(animate=True)
        self.play(dot.animate.shift(LEFT * 2))
        self.wait()


class Sec07_ZoomedScene_MovingFrame(ZoomedScene):
    """ZoomedScene -- move and scale the zoomed camera frame."""
    def __init__(self, **kwargs):
        ZoomedScene.__init__(
            self,
            zoom_factor=0.3,
            zoomed_display_height=1,
            zoomed_display_width=3,
            image_frame_stroke_width=20,
            zoomed_camera_config={"default_frame_stroke_width": 3},
            **kwargs
        )

    def construct(self):
        dot = Dot(color=GREEN)
        sq = Circle(fill_opacity=1, radius=0.2, color=BLUE).next_to(dot, RIGHT)
        self.add(dot, sq)
        self.activate_zooming(animate=False)
        self.play(dot.animate.shift(LEFT * 0.3))
        # Scale the zoomed camera frame (changes zoom level)
        self.play(self.zoomed_camera.frame.animate.scale(4))
        # Move the zoomed camera frame
        self.play(self.zoomed_camera.frame.animate.shift(0.5 * DOWN))
        self.wait()


# =============================================================================
# SECTION 8: UpdateFromFunc AND UpdateFromAlphaFunc
# (manim/animation/updaters/update.py)
# =============================================================================

class Sec08_UpdateFromFunc(Scene):
    """UpdateFromFunc -- call a function on the mobject every frame.
    The function receives (mobject) only; alpha is NOT passed."""
    def construct(self):
        dot = Dot(color=RED)
        num = DecimalNumber(0).next_to(dot, UP)
        self.add(dot, num)

        # UpdateFromFunc: called every frame with the mobject
        self.play(
            dot.animate.shift(RIGHT * 4),
            UpdateFromFunc(num, lambda m: m.next_to(dot, UP)),
            run_time=3,
        )
        self.wait()


class Sec08_UpdateFromAlphaFunc(Scene):
    """UpdateFromAlphaFunc -- like UpdateFromFunc but also receives alpha (0..1).
    The function receives (mobject, alpha)."""
    def construct(self):
        dot = Dot(color=BLUE)
        self.add(dot)

        def update(mob, alpha):
            mob.move_to(RIGHT * 4 * alpha + UP * 2 * np.sin(alpha * TAU))
            mob.set_color(interpolate_color(BLUE, RED, alpha))

        self.play(UpdateFromAlphaFunc(dot, update), run_time=3)
        self.wait()


class Sec08_UpdateFromAlphaFunc_NumberCounter(Scene):
    """UpdateFromAlphaFunc to animate a number counter."""
    def construct(self):
        num = DecimalNumber(0, num_decimal_places=0, font_size=72)
        self.add(num)

        self.play(UpdateFromAlphaFunc(
            num,
            lambda m, a: m.set_value(int(100 * a)),
        ), run_time=3)
        self.wait()


class Sec08_MaintainPositionRelativeTo(Scene):
    """MaintainPositionRelativeTo -- keep constant offset to a tracked mobject."""
    def construct(self):
        dot = Dot(color=RED)
        label = Text("Label", font_size=24).next_to(dot, UP)
        self.add(dot, label)

        self.play(
            dot.animate.shift(RIGHT * 3 + UP * 2),
            MaintainPositionRelativeTo(label, dot),
            run_time=2,
        )
        self.wait()


# =============================================================================
# SECTION 9: always_redraw PATTERNS
# (manim/animation/updaters/mobject_update_utils.py)
# =============================================================================

class Sec09_AlwaysRedraw_Basic(Scene):
    """always_redraw -- re-create a mobject every frame from a function."""
    def construct(self):
        tracker = ValueTracker(0)
        # The lambda is called every frame; the returned mobject replaces the old one
        dot = always_redraw(lambda: Dot(
            point=RIGHT * tracker.get_value(),
            color=BLUE,
        ))
        self.add(dot)
        self.play(tracker.animate.set_value(4), run_time=3, rate_func=linear)
        self.wait()


class Sec09_AlwaysRedraw_Line(Scene):
    """always_redraw to draw a dynamic line between two moving points."""
    def construct(self):
        d1 = Dot(LEFT * 3, color=RED)
        d2 = Dot(RIGHT * 3, color=BLUE)
        line = always_redraw(lambda: Line(
            d1.get_center(), d2.get_center(), color=YELLOW
        ))
        self.add(d1, d2, line)
        self.play(
            d1.animate.shift(UP * 2),
            d2.animate.shift(DOWN * 2),
            run_time=2,
        )
        self.wait()


class Sec09_AlwaysRedraw_ValueTracker(Scene):
    """Classic 3b1b pattern: ValueTracker + always_redraw for dynamic scenes."""
    def construct(self):
        ax = Axes(x_range=[-3, 3], y_range=[-2, 2])
        alpha = ValueTracker(0)

        sine = ax.plot(np.sin, color=RED)
        point = always_redraw(lambda: Dot(
            sine.point_from_proportion(alpha.get_value()),
            color=BLUE,
        ))
        tangent = always_redraw(lambda: TangentLine(
            sine,
            alpha=alpha.get_value(),
            color=YELLOW,
            length=4,
        ))
        self.add(ax, sine, point, tangent)
        self.play(alpha.animate.set_value(1), rate_func=linear, run_time=4)
        self.wait()


class Sec09_AlwaysRedraw_DecimalNumber(Scene):
    """always_redraw with DecimalNumber tracking a ValueTracker."""
    def construct(self):
        tracker = ValueTracker(0)
        number = always_redraw(lambda: DecimalNumber(
            tracker.get_value(),
            num_decimal_places=2,
            font_size=72,
        ).to_edge(UP))

        self.add(number)
        self.play(tracker.animate.set_value(10), run_time=3, rate_func=linear)
        self.wait()


class Sec09_AlwaysShift(Scene):
    """always_shift -- continuously shift a mobject in a direction."""
    def construct(self):
        sq = Square(color=BLUE, fill_opacity=0.5)
        always_shift(sq, RIGHT, rate=2)  # 2 units/sec to the right
        self.add(sq)
        self.wait(3)


class Sec09_AlwaysRotate(Scene):
    """always_rotate -- continuously rotate a mobject."""
    def construct(self):
        tri = Triangle(color=RED, fill_opacity=0.5).set_z_index(2)
        sq = Square(color=BLUE).to_edge(LEFT)
        always_rotate(tri, rate=2 * PI, about_point=ORIGIN)
        self.add(tri, sq)
        self.play(sq.animate.to_edge(RIGHT), rate_func=linear, run_time=2)
        self.wait()


class Sec09_AddUpdater_Manual(Scene):
    """Manual .add_updater() pattern -- most flexible approach."""
    def construct(self):
        dot = Dot(color=RED)
        label = Text("pos", font_size=20)

        # Updater receives (mobject, dt)
        label.add_updater(lambda m, dt: m.next_to(dot, UP, buff=0.1))

        self.add(dot, label)
        self.play(dot.animate.shift(RIGHT * 3 + UP * 2), run_time=2)
        self.wait()


class Sec09_TurnAnimationIntoUpdater(Scene):
    """turn_animation_into_updater -- convert an animation to a persistent updater."""
    def construct(self):
        words = Text("Welcome to")
        banner = ManimBanner().scale(0.5)
        VGroup(words, banner).arrange(DOWN)

        turn_animation_into_updater(Write(words, run_time=0.9))
        self.add(words)
        self.wait(1)
        self.play(banner.expand(), run_time=0.5)
        self.wait()


class Sec09_CycleAnimation(Scene):
    """cycle_animation -- repeating animation as an updater."""
    def construct(self):
        sq = Square(color=BLUE)
        cycle_animation(Rotating(sq, run_time=2))
        self.add(sq)
        self.wait(6)  # Rotates 3 full cycles


class Sec09_TracedPath(Scene):
    """TracedPath -- automatically trace a point's motion path."""
    def construct(self):
        circ = Circle(color=RED).shift(4 * LEFT)
        dot = Dot(color=RED).move_to(circ.get_start())
        rolling = VGroup(circ, dot)
        trace = TracedPath(circ.get_start)
        rolling.add_updater(lambda m: m.rotate(-0.3))
        self.add(trace, rolling)
        self.play(rolling.animate.shift(8 * RIGHT), run_time=4, rate_func=linear)
        self.wait()


class Sec09_TracedPath_Dissipating(Scene):
    """TracedPath with dissipating_time -- trail fades over time."""
    def construct(self):
        a = Dot(RIGHT * 2, color=YELLOW)
        b = TracedPath(a.get_center, dissipating_time=0.5, stroke_opacity=[0, 1])
        self.add(a, b)
        self.play(a.animate(path_arc=PI / 4).shift(LEFT * 2))
        self.play(a.animate(path_arc=-PI / 4).shift(LEFT * 2))
        self.wait()


class Sec09_AnimatedBoundary(Scene):
    """AnimatedBoundary -- animated color-cycling border around a VMobject."""
    def construct(self):
        text = Text("So shiny!")
        boundary = AnimatedBoundary(text, colors=[RED, GREEN, BLUE], cycle_rate=3)
        self.add(text, boundary)
        self.wait(3)


# =============================================================================
# SECTION 10: RATE FUNCTIONS (manim/utils/rate_functions.py)
# =============================================================================
# EXPORTED (can be used directly):
#   linear, smooth, smoothstep, smootherstep, smoothererstep,
#   rush_into, rush_from, slow_into, double_smooth,
#   there_and_back, there_and_back_with_pause, running_start,
#   not_quite_there, wiggle, squish_rate_func,
#   lingering, exponential_decay
#
# NON-EXPORTED (use via rate_functions.xxx):
#   ease_in_sine, ease_out_sine, ease_in_out_sine,
#   ease_in_quad, ease_out_quad, ease_in_out_quad,
#   ease_in_cubic, ease_out_cubic, ease_in_out_cubic,
#   ease_in_quart, ease_out_quart, ease_in_out_quart,
#   ease_in_quint, ease_out_quint, ease_in_out_quint,
#   ease_in_expo, ease_out_expo, ease_in_out_expo,
#   ease_in_circ, ease_out_circ, ease_in_out_circ,
#   ease_in_back, ease_out_back, ease_in_out_back,
#   ease_in_elastic, ease_out_elastic, ease_in_out_elastic,
#   ease_in_bounce, ease_out_bounce, ease_in_out_bounce

class Sec10_RateFunc_Exported(Scene):
    """Demonstration of all exported rate functions."""
    def construct(self):
        funcs = [
            ("linear", linear),
            ("smooth", smooth),
            ("rush_into", rush_into),
            ("rush_from", rush_from),
            ("slow_into", slow_into),
            ("double_smooth", double_smooth),
            ("there_and_back", there_and_back),
            ("running_start", running_start),
            ("lingering", lingering),
            ("exponential_decay", exponential_decay),
        ]
        lines = VGroup()
        for i, (name, func) in enumerate(funcs):
            line = Line(LEFT * 5, RIGHT * 5).shift(DOWN * (i - len(funcs) / 2) * 0.5)
            label = Text(name, font_size=16).next_to(line, LEFT)
            dot = Dot(color=YELLOW).move_to(line.get_start())
            lines.add(VGroup(line, label, dot))

        self.add(lines)
        self.play(*[
            MoveAlongPath(g[2], g[0], rate_func=funcs[i][1])
            for i, g in enumerate(lines)
        ], run_time=4)
        self.wait()


class Sec10_RateFunc_ThereAndBack(Scene):
    """there_and_back -- goes to end and returns. there_and_back(0.5) = 1."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(sq.animate.shift(RIGHT * 3), rate_func=there_and_back, run_time=2)
        self.wait()


class Sec10_RateFunc_ThereAndBackWithPause(Scene):
    """there_and_back_with_pause -- pause at the peak.
    Parameters: pause_ratio=1/3."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(
            sq.animate.shift(RIGHT * 3),
            rate_func=there_and_back_with_pause,
            run_time=3,
        )
        self.wait()


class Sec10_RateFunc_RunningStart(Scene):
    """running_start -- pulls back before accelerating.
    Parameters: pull_factor=-0.5."""
    def construct(self):
        dot = Dot(color=RED).shift(LEFT * 3)
        self.add(dot)
        self.play(
            dot.animate.shift(RIGHT * 6),
            rate_func=running_start,
            run_time=2,
        )
        self.wait()


class Sec10_RateFunc_NotQuiteThere(Scene):
    """not_quite_there -- only reaches proportion of the way.
    Parameters: func=smooth, proportion=0.7."""
    def construct(self):
        sq = Square(color=BLUE).shift(LEFT * 3)
        target = RIGHT * 3
        self.add(sq, Dot(target, color=RED))  # Red dot marks the "full" destination
        self.play(
            sq.animate.move_to(target),
            rate_func=not_quite_there(smooth, 0.7),
            run_time=2,
        )
        self.wait()


class Sec10_RateFunc_SquishRateFunc(Scene):
    """squish_rate_func -- compress a rate func into a sub-interval.
    Parameters: func, a=0.4, b=0.6."""
    def construct(self):
        d1 = Dot(color=RED).shift(LEFT * 3 + UP)
        d2 = Dot(color=BLUE).shift(LEFT * 3 + DOWN)
        self.add(d1, d2)
        # d1: smooth spread over full time
        # d2: smooth squished into 20%-80% of the time
        self.play(
            d1.animate.shift(RIGHT * 6),
            d2.animate(rate_func=squish_rate_func(smooth, 0.2, 0.8)).shift(RIGHT * 6),
            run_time=3,
        )
        self.wait()


class Sec10_RateFunc_Wiggle(Scene):
    """wiggle rate func -- oscillates with there_and_back envelope.
    Parameters: wiggles=2."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(
            sq.animate.shift(RIGHT * 3),
            rate_func=wiggle,
            run_time=3,
        )
        self.wait()


class Sec10_RateFunc_EasingStandard(Scene):
    """Standard easing functions (not exported -- use rate_functions.xxx)."""
    def construct(self):
        # These must be accessed via the module
        from manim.utils import rate_functions as rf

        dot1 = Dot(color=RED).shift(LEFT * 5 + UP * 2)
        dot2 = Dot(color=GREEN).shift(LEFT * 5)
        dot3 = Dot(color=BLUE).shift(LEFT * 5 + DOWN * 2)

        l1 = Text("ease_in_elastic", font_size=16).next_to(dot1, UP)
        l2 = Text("ease_out_bounce", font_size=16).next_to(dot2, UP)
        l3 = Text("ease_in_out_back", font_size=16).next_to(dot3, UP)

        self.add(dot1, dot2, dot3, l1, l2, l3)
        self.play(
            dot1.animate.shift(RIGHT * 10),
            dot2.animate.shift(RIGHT * 10),
            dot3.animate.shift(RIGHT * 10),
            rate_func=linear,  # each dot overrides below
            run_time=4,
        )
        # To actually apply per-dot:
        self.play(AnimationGroup(
            dot1.animate(rate_func=rf.ease_in_elastic).shift(LEFT * 10),
            dot2.animate(rate_func=rf.ease_out_bounce).shift(LEFT * 10),
            dot3.animate(rate_func=rf.ease_in_out_back).shift(LEFT * 10),
            run_time=4,
        ))
        self.wait()


class Sec10_RateFunc_AllEasing(Scene):
    """Full catalog of easing functions available via rate_functions module."""
    def construct(self):
        from manim.utils import rate_functions as rf
        # Complete list of all ease_* functions:
        all_ease = [
            # Sine
            ("ease_in_sine", rf.ease_in_sine),
            ("ease_out_sine", rf.ease_out_sine),
            ("ease_in_out_sine", rf.ease_in_out_sine),
            # Quad (power of 2)
            ("ease_in_quad", rf.ease_in_quad),
            ("ease_out_quad", rf.ease_out_quad),
            ("ease_in_out_quad", rf.ease_in_out_quad),
            # Cubic (power of 3)
            ("ease_in_cubic", rf.ease_in_cubic),
            ("ease_out_cubic", rf.ease_out_cubic),
            ("ease_in_out_cubic", rf.ease_in_out_cubic),
            # Quart (power of 4)
            ("ease_in_quart", rf.ease_in_quart),
            ("ease_out_quart", rf.ease_out_quart),
            ("ease_in_out_quart", rf.ease_in_out_quart),
            # Quint (power of 5)
            ("ease_in_quint", rf.ease_in_quint),
            ("ease_out_quint", rf.ease_out_quint),
            ("ease_in_out_quint", rf.ease_in_out_quint),
            # Expo (exponential)
            ("ease_in_expo", rf.ease_in_expo),
            ("ease_out_expo", rf.ease_out_expo),
            ("ease_in_out_expo", rf.ease_in_out_expo),
            # Circ (circular)
            ("ease_in_circ", rf.ease_in_circ),
            ("ease_out_circ", rf.ease_out_circ),
            ("ease_in_out_circ", rf.ease_in_out_circ),
            # Back (overshoot)
            ("ease_in_back", rf.ease_in_back),
            ("ease_out_back", rf.ease_out_back),
            ("ease_in_out_back", rf.ease_in_out_back),
            # Elastic
            ("ease_in_elastic", rf.ease_in_elastic),
            ("ease_out_elastic", rf.ease_out_elastic),
            ("ease_in_out_elastic", rf.ease_in_out_elastic),
            # Bounce
            ("ease_in_bounce", rf.ease_in_bounce),
            ("ease_out_bounce", rf.ease_out_bounce),
            ("ease_in_out_bounce", rf.ease_in_out_bounce),
        ]
        info = Text(f"Total: {len(all_ease)} standard easing functions", font_size=24)
        self.add(info)
        self.wait()


class Sec10_Smoothstep_Variants(Scene):
    """smoothstep, smootherstep, smoothererstep -- SmoothStep family."""
    def construct(self):
        d1 = Dot(color=RED).shift(LEFT * 4 + UP)
        d2 = Dot(color=GREEN).shift(LEFT * 4)
        d3 = Dot(color=BLUE).shift(LEFT * 4 + DOWN)

        self.add(d1, d2, d3)
        self.add(
            Text("smoothstep", font_size=14).next_to(d1, UP),
            Text("smootherstep", font_size=14).next_to(d2, UP),
            Text("smoothererstep", font_size=14).next_to(d3, UP),
        )
        self.play(AnimationGroup(
            d1.animate(rate_func=smoothstep).shift(RIGHT * 8),
            d2.animate(rate_func=smootherstep).shift(RIGHT * 8),
            d3.animate(rate_func=smoothererstep).shift(RIGHT * 8),
            run_time=3,
        ))
        self.wait()


# =============================================================================
# SECTION 11: CUSTOM ANIMATION CLASSES
# =============================================================================

class Sec11_CustomAnimation_Subclass(Scene):
    """Creating a custom animation by subclassing Animation."""
    def construct(self):
        class Pulse(Animation):
            """Custom animation that pulses an object's scale."""
            def __init__(self, mobject, scale_factor=1.5, n_pulses=3, **kwargs):
                self.scale_factor = scale_factor
                self.n_pulses = n_pulses
                super().__init__(mobject, **kwargs)

            def interpolate_mobject(self, alpha):
                # Use rate_func to get actual progress
                t = self.rate_func(alpha)
                scale = 1 + (self.scale_factor - 1) * abs(np.sin(t * self.n_pulses * PI))
                self.mobject.become(self.starting_mobject)
                self.mobject.scale(scale)

        sq = Square(color=BLUE)
        self.add(sq)
        self.play(Pulse(sq, scale_factor=1.5, n_pulses=4, run_time=3))
        self.wait()


class Sec11_CustomTransform_Subclass(Scene):
    """Creating a custom Transform subclass."""
    def construct(self):
        class GrowAndSpin(Transform):
            """Grow from center with a spin."""
            def __init__(self, mobject, angle=TAU, **kwargs):
                self.angle = angle
                super().__init__(mobject, introducer=True, **kwargs)

            def create_target(self):
                return self.mobject

            def create_starting_mobject(self):
                start = self.mobject.copy()
                start.scale(0)
                start.rotate(self.angle)
                return start

        sq = Square(color=RED, fill_opacity=0.5)
        self.play(GrowAndSpin(sq, angle=2 * PI))
        self.wait()


class Sec11_OverrideAnimation(Scene):
    """Using @override_animation decorator on Mobject subclasses."""
    def construct(self):
        class MySquare(Square):
            @override_animation(FadeIn)
            def _fade_in_override(self, **kwargs):
                return Create(self, **kwargs)

        sq = MySquare(color=GREEN)
        # FadeIn is overridden to Create for MySquare
        self.play(FadeIn(sq))
        self.wait()


class Sec11_AnimationSetDefault(Scene):
    """Using Animation.set_default() to change default parameters."""
    def construct(self):
        Rotate.set_default(run_time=2, rate_func=linear)
        Indicate.set_default(color=None)

        sq = Square(color=BLUE, fill_color=BLUE, fill_opacity=0.25)
        self.add(sq)
        self.play(Rotate(sq, PI))       # Uses run_time=2, rate_func=linear
        self.play(Indicate(sq))         # Uses color=None (keeps original)

        # Reset to original defaults
        Rotate.set_default()
        Indicate.set_default()
        self.wait()


# =============================================================================
# SECTION 12: SCENE TRANSITIONS AND MISCELLANEOUS
# =============================================================================

# NOTE: Manim CE does NOT have built-in scene transition animations like
# crossfade or wipe as dedicated classes. Instead, transitions between
# "scenes" (sections of construct()) are achieved through composition:

class Sec12_CrossfadeTransition(Scene):
    """Simulating a crossfade transition between two scene states."""
    def construct(self):
        # Scene 1
        scene1 = VGroup(
            Square(color=BLUE, fill_opacity=0.5),
            Text("Scene 1", font_size=36).shift(DOWN * 1.5),
        )
        # Scene 2
        scene2 = VGroup(
            Circle(color=RED, fill_opacity=0.5),
            Text("Scene 2", font_size=36).shift(DOWN * 1.5),
        )
        scene2.shift(RIGHT * 0.01)  # tiny shift to avoid overlap issues

        self.add(scene1)
        self.wait()
        # Crossfade: simultaneous FadeOut old + FadeIn new
        self.play(
            FadeOut(scene1),
            FadeIn(scene2),
        )
        self.wait()


class Sec12_SlideTransition(Scene):
    """Simulating a slide/wipe transition."""
    def construct(self):
        scene1 = VGroup(
            Square(color=BLUE, fill_opacity=0.5),
            Text("Scene 1", font_size=36).shift(DOWN * 1.5),
        )
        scene2 = VGroup(
            Circle(color=RED, fill_opacity=0.5),
            Text("Scene 2", font_size=36).shift(DOWN * 1.5),
        ).shift(RIGHT * 14)  # start off-screen

        self.add(scene1, scene2)
        self.wait()
        # Wipe: slide both left simultaneously
        self.play(
            scene1.animate.shift(LEFT * 14),
            scene2.animate.shift(LEFT * 14),
            run_time=1.5,
        )
        self.wait()


class Sec12_FadeTransformTransition(Scene):
    """Using FadeTransform for smooth morph-based transitions."""
    def construct(self):
        title1 = Text("Introduction", font_size=48, color=BLUE)
        title2 = Text("Main Content", font_size=48, color=RED)
        self.add(title1)
        self.wait()
        self.play(FadeTransform(title1, title2))
        self.wait()


# =============================================================================
# SECTION 12b: GROWING ANIMATIONS (manim/animation/growing.py)
# =============================================================================

class Sec12b_GrowFromPoint(Scene):
    """GrowFromPoint -- grow from a specified point.
    Parameters: point, point_color=None."""
    def construct(self):
        sq = Square(color=BLUE)
        self.play(GrowFromPoint(sq, ORIGIN))
        self.wait()


class Sec12b_GrowFromPoint_Color(Scene):
    """GrowFromPoint with initial color."""
    def construct(self):
        sq = Square(color=BLUE)
        self.play(GrowFromPoint(sq, LEFT * 3 + DOWN * 2, point_color=RED))
        self.wait()


class Sec12b_GrowFromCenter(Scene):
    """GrowFromCenter -- grow from the mobject's own center."""
    def construct(self):
        ci = Circle(color=GREEN)
        self.play(GrowFromCenter(ci))
        self.wait()


class Sec12b_GrowFromEdge(Scene):
    """GrowFromEdge -- grow from a specific edge (DOWN, UP, LEFT, RIGHT, UR, etc.)."""
    def construct(self):
        squares = [Square(color=c) for c in [RED, GREEN, BLUE, YELLOW]]
        VGroup(*squares).arrange(RIGHT, buff=1)
        self.play(GrowFromEdge(squares[0], DOWN))
        self.play(GrowFromEdge(squares[1], RIGHT))
        self.play(GrowFromEdge(squares[2], UR))
        self.play(GrowFromEdge(squares[3], UP))
        self.wait()


class Sec12b_GrowArrow(Scene):
    """GrowArrow -- grow an arrow from its start point."""
    def construct(self):
        arrow = Arrow(2 * LEFT, 2 * RIGHT, color=BLUE)
        self.play(GrowArrow(arrow))
        self.wait()


class Sec12b_SpinInFromNothing(Scene):
    """SpinInFromNothing -- grow from center with a spin.
    Parameters: angle=PI/2, point_color=None."""
    def construct(self):
        sq = Square(color=RED)
        self.play(SpinInFromNothing(sq))
        self.wait()


class Sec12b_SpinInFromNothing_FullSpin(Scene):
    """SpinInFromNothing with a full 360-degree spin."""
    def construct(self):
        sq = Square(color=BLUE)
        self.play(SpinInFromNothing(sq, angle=2 * PI))
        self.wait()


# =============================================================================
# SECTION 12c: ROTATION ANIMATIONS (manim/animation/rotation.py)
# =============================================================================

class Sec12c_Rotating(Scene):
    """Rotating -- continuous rotation (re-rotates from starting state each frame).
    Parameters: angle=TAU, axis=OUT, about_point=None, about_edge=None,
                run_time=5, rate_func=linear."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(Rotating(sq, angle=TAU, run_time=2))
        self.wait()


class Sec12c_Rotating_AboutPoint(Scene):
    """Rotating about an external point."""
    def construct(self):
        dot = Dot(ORIGIN, color=RED)
        sq = Square(side_length=0.5, color=BLUE).shift(RIGHT * 2)
        self.add(dot, sq)
        self.play(Rotating(sq, angle=2 * PI, about_point=ORIGIN, run_time=3))
        self.wait()


class Sec12c_Rotate(Scene):
    """Rotate (Transform-based) -- smooth rotation with interpolation.
    Parameters: angle=PI, axis=OUT, about_point=None, about_edge=None."""
    def construct(self):
        sq = Square(side_length=0.5, color=BLUE).shift(UP * 2)
        self.add(sq)
        self.play(
            Rotate(sq, angle=2 * PI, about_point=ORIGIN, rate_func=linear),
        )
        self.wait()


class Sec12c_Rotate_InPlace(Scene):
    """Rotate in place (default: about_point=center)."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)
        self.play(Rotate(sq, angle=PI / 2))
        self.wait()


# =============================================================================
# SECTION 12d: MOVEMENT ANIMATIONS (manim/animation/movement.py)
# =============================================================================

class Sec12d_Homotopy(Scene):
    """Homotopy -- continuously deform points via f(x,y,z,t) -> (x',y',z').
    Parameters: run_time=3."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)

        def homotopy(x, y, z, t):
            return (x + t * 0.5, y + 0.3 * np.sin(x * 3 + t * 5), z)

        self.play(Homotopy(homotopy, sq, rate_func=linear, run_time=3))
        self.wait()


class Sec12d_ComplexHomotopy(Scene):
    """ComplexHomotopy -- homotopy using complex function f(z, t)."""
    def construct(self):
        plane = NumberPlane()
        self.add(plane)

        def complex_func(z, t):
            return z * np.exp(1j * t * PI)  # Rotate in complex plane

        self.play(ComplexHomotopy(complex_func, plane, run_time=3))
        self.wait()


class Sec12d_PhaseFlow(Scene):
    """PhaseFlow -- apply a vector field flow.
    Parameters: function, virtual_time=1, rate_func=linear."""
    def construct(self):
        plane = NumberPlane()
        self.add(plane)
        self.play(PhaseFlow(
            lambda p: np.array([p[1], -p[0], 0]),  # Rotation field
            plane,
            virtual_time=2,
            run_time=3,
        ))
        self.wait()


class Sec12d_MoveAlongPath(Scene):
    """MoveAlongPath -- move a mobject along a VMobject path."""
    def construct(self):
        dot = Dot(color=ORANGE)
        path = Circle(radius=2, color=BLUE)
        self.add(path, dot)
        self.play(MoveAlongPath(dot, path), rate_func=linear, run_time=3)
        self.wait()


class Sec12d_MoveAlongPath_Custom(Scene):
    """MoveAlongPath along a custom curve."""
    def construct(self):
        dot = Dot(color=RED)
        path = VMobject()
        path.set_points_smoothly([
            LEFT * 3 + DOWN,
            LEFT + UP * 2,
            RIGHT + DOWN,
            RIGHT * 3 + UP * 2,
        ])
        path.set_color(YELLOW)
        self.add(path, dot)
        self.play(MoveAlongPath(dot, path), rate_func=linear, run_time=3)
        self.wait()


# =============================================================================
# SECTION 12e: NUMBER ANIMATIONS (manim/animation/numbers.py)
# =============================================================================

class Sec12e_ChangingDecimal(Scene):
    """ChangingDecimal -- animate a DecimalNumber via a function of alpha."""
    def construct(self):
        number = DecimalNumber(0, font_size=72)
        self.add(number)
        # Function receives alpha (0 to 1)
        self.play(ChangingDecimal(number, lambda a: 5 * a), run_time=3)
        self.wait()


class Sec12e_ChangeDecimalToValue(Scene):
    """ChangeDecimalToValue -- animate from current value to target value."""
    def construct(self):
        number = DecimalNumber(0, font_size=72)
        self.add(number)
        self.play(ChangeDecimalToValue(number, 100, run_time=3))
        self.wait()


# =============================================================================
# SECTION 12f: SPECIALIZED ANIMATIONS (manim/animation/specialized.py)
# =============================================================================

class Sec12f_Broadcast(Scene):
    """Broadcast -- expanding concentric copies emanate from focal point.
    Parameters: focal_point=ORIGIN, n_mobs=5, initial_opacity=1,
                final_opacity=0, initial_width=0, remover=True,
                lag_ratio=0.2, run_time=3."""
    def construct(self):
        mob = Circle(radius=4, color=TEAL_A)
        self.play(Broadcast(mob))
        self.wait()


class Sec12f_Broadcast_Custom(Scene):
    """Broadcast with custom parameters."""
    def construct(self):
        sq = Square(color=RED, stroke_width=3)
        self.play(Broadcast(
            sq,
            focal_point=ORIGIN,
            n_mobs=8,
            initial_opacity=1,
            final_opacity=0,
            initial_width=0.5,
            lag_ratio=0.1,
            run_time=4,
        ))
        self.wait()


# =============================================================================
# SECTION 12g: SPEED MODIFIER (manim/animation/speedmodifier.py)
# =============================================================================

class Sec12g_ChangeSpeed(Scene):
    """ChangeSpeed -- modify the speed of an animation dynamically.
    speedinfo dict maps progress fraction (0..1) to speed factor."""
    def construct(self):
        a = Dot(color=RED).shift(LEFT * 4)
        b = Dot(color=BLUE).shift(RIGHT * 4)
        self.add(a, b)
        self.play(
            ChangeSpeed(
                AnimationGroup(
                    a.animate(run_time=1).shift(RIGHT * 8),
                    b.animate(run_time=1).shift(LEFT * 8),
                ),
                speedinfo={0.3: 1, 0.4: 0.1, 0.6: 0.1, 1: 1},
                rate_func=linear,
            )
        )
        self.wait()


class Sec12g_ChangeSpeed_Updater(Scene):
    """ChangeSpeed.add_updater -- speed-aware updaters."""
    def construct(self):
        a = Dot(color=BLUE).shift(LEFT * 4)
        self.add(a)
        ChangeSpeed.add_updater(a, lambda x, dt: x.shift(RIGHT * 4 * dt))
        self.play(
            ChangeSpeed(
                Wait(2),
                speedinfo={0.4: 1, 0.5: 0.2, 0.8: 0.2, 1: 1},
                affects_speed_updaters=True,
            )
        )
        self.wait()


# =============================================================================
# SECTION 12h: BASE ANIMATION CLASS FEATURES (manim/animation/animation.py)
# =============================================================================

class Sec12h_Wait(Scene):
    """Wait -- a 'no operation' animation.
    Parameters: run_time=1, stop_condition=None, frozen_frame=None."""
    def construct(self):
        text = Text("Waiting...", font_size=48)
        self.add(text)
        self.wait(2)  # uses Wait internally
        # Can also be used explicitly in Succession:
        self.play(Succession(
            FadeOut(text),
            Wait(1),
            FadeIn(Text("Done!", font_size=48)),
        ))
        self.wait()


class Sec12h_Add(Scene):
    """Add -- instant introduction of mobjects (0 run_time by default)."""
    def construct(self):
        text1 = Text("First!", font_size=48).shift(UP)
        text2 = Text("Second!", font_size=48).shift(DOWN)
        rect = SurroundingRectangle(VGroup(text1, text2), buff=0.5)

        self.play(
            Create(rect, run_time=3.0),
            Succession(
                Wait(1.0),
                Add(text1),           # Instant add in the middle
                Wait(1.0),
                Add(text2),
            ),
        )
        self.wait()


# =============================================================================
# SECTION 12i: .animate SYNTAX -- COMPREHENSIVE GUIDE
# =============================================================================

class Sec12i_AnimateSyntax(Scene):
    """The .animate property creates a MoveToTarget animation builder.
    Any chained method calls are recorded and applied to a generated target."""
    def construct(self):
        sq = Square(color=BLUE)
        self.add(sq)

        # Single method
        self.play(sq.animate.set_color(RED))
        # Multiple chained methods
        self.play(sq.animate.shift(RIGHT * 2).scale(0.5).rotate(PI / 4))
        # With custom animation parameters
        self.play(
            sq.animate(run_time=2, rate_func=there_and_back).shift(UP * 2)
        )
        # With path_arc for curved motion
        self.play(sq.animate(path_arc=PI / 2).shift(LEFT * 4))
        self.wait()


class Sec12i_AnimateLagRatio(Scene):
    """Using lag_ratio with .animate on VGroups."""
    def construct(self):
        group = VGroup(*[Dot() for _ in range(4)]).arrange(RIGHT, buff=1)
        self.add(group)

        # lag_ratio on .animate distributes the animation across submobjects
        self.play(group.animate(lag_ratio=0.5, run_time=2).shift(DOWN * 2))
        self.wait()


# =============================================================================
# COMPLETE ANIMATION CLASS INVENTORY
# =============================================================================
"""
COMPLETE LIST OF ALL ANIMATION CLASSES IN MANIM CE
(derived from __all__ exports of every animation module)

FROM animation.py:
  - Animation           (base class)
  - Wait                (no-op animation)
  - Add                 (instant introduction)
  - override_animation  (decorator)

FROM fading.py:
  - FadeIn              (fade in with shift/scale/target_position)
  - FadeOut             (fade out with shift/scale/target_position)

FROM transform.py:
  - Transform           (morph source into target)
  - ReplacementTransform (morph + replace source with target)
  - TransformFromCopy   (morph a copy, preserve original)
  - ClockwiseTransform  (clockwise arc path)
  - CounterclockwiseTransform (CCW arc path)
  - MoveToTarget        (animate to .target attribute)
  - ApplyMethod         (animate a bound method)
  - ApplyPointwiseFunction (transform each point)
  - ApplyPointwiseFunctionToCenter (transform center)
  - FadeToColor         (animate color change)
  - FadeTransform       (cross-fade morph)
  - FadeTransformPieces (cross-fade submobjects)
  - ScaleInPlace        (animate scale)
  - ShrinkToCenter      (shrink to zero)
  - Restore             (return to saved state)
  - ApplyFunction       (arbitrary function returning Mobject)
  - ApplyMatrix         (matrix transformation)
  - ApplyComplexFunction (complex function transformation)
  - CyclicReplace       (cyclic position swap)
  - Swap                (two-element CyclicReplace)
  - TransformAnimations (morph between two animations)

FROM transform_matching_parts.py:
  - TransformMatchingShapes (match by point hash)
  - TransformMatchingTex    (match by tex_string)

FROM creation.py:
  - Create              (draw stroke incrementally)
  - Uncreate            (reverse of Create)
  - DrawBorderThenFill  (outline then fill)
  - Write               (hand-writing effect)
  - Unwrite             (reverse of Write)
  - ShowPartial         (abstract base)
  - ShowIncreasingSubsets (cumulative submobject reveal)
  - SpiralIn            (spiral trajectory entry)
  - AddTextLetterByLetter (typewriter effect)
  - RemoveTextLetterByLetter (reverse typewriter)
  - ShowSubmobjectsOneByOne (one at a time, replacing)
  - AddTextWordByWord   (word-by-word, currently broken)
  - TypeWithCursor      (typewriter with cursor)
  - UntypeWithCursor    (reverse with cursor)

FROM indication.py:
  - FocusOn             (spotlight shrink)
  - Indicate            (scale + recolor pulse)
  - Flash               (radial line burst)
  - ShowPassingFlash    (traveling sliver)
  - ShowPassingFlashWithThinningStrokeWidth (layered traveling sliver)
  - ApplyWave           (wave distortion)
  - Circumscribe        (temporary surrounding shape)
  - Wiggle              (scale + rotation oscillation)
  - Blink               (visibility toggle)

FROM composition.py:
  - AnimationGroup      (parallel with lag_ratio)
  - Succession          (sequential, lag_ratio=1)
  - LaggedStart         (staggered start, lag_ratio=0.05)
  - LaggedStartMap      (LaggedStart + map to submobjects)

FROM growing.py:
  - GrowFromPoint       (grow from a point)
  - GrowFromCenter      (grow from center)
  - GrowFromEdge        (grow from an edge)
  - GrowArrow           (grow arrow from start)
  - SpinInFromNothing   (grow + spin from center)

FROM rotation.py:
  - Rotating            (continuous rotation)
  - Rotate              (Transform-based rotation)

FROM movement.py:
  - Homotopy            (continuous point deformation)
  - SmoothedVectorizedHomotopy (smooth homotopy)
  - ComplexHomotopy     (complex function homotopy)
  - PhaseFlow           (vector field flow)
  - MoveAlongPath       (follow a VMobject path)

FROM numbers.py:
  - ChangingDecimal     (animate DecimalNumber via function)
  - ChangeDecimalToValue (animate to target number)

FROM specialized.py:
  - Broadcast           (expanding concentric copies)

FROM speedmodifier.py:
  - ChangeSpeed         (dynamic speed modification)

FROM updaters/update.py:
  - UpdateFromFunc      (per-frame function call)
  - UpdateFromAlphaFunc (per-frame with alpha)
  - MaintainPositionRelativeTo (track another mobject)

FROM updaters/mobject_update_utils.py (utility functions, not classes):
  - always_redraw       (re-create mobject every frame)
  - always_shift        (continuous shift)
  - always_rotate       (continuous rotation)
  - always              (call a method every frame)
  - f_always            (functional version of always)
  - turn_animation_into_updater (convert animation to updater)
  - cycle_animation     (repeating animation updater)

FROM changing.py (not animations, but updater mobjects):
  - AnimatedBoundary    (color-cycling boundary)
  - TracedPath          (trace a point's movement)

RATE FUNCTIONS (manim/utils/rate_functions.py):
  Exported:
    linear, smooth, smoothstep, smootherstep, smoothererstep,
    rush_into, rush_from, slow_into, double_smooth,
    there_and_back, there_and_back_with_pause, running_start,
    not_quite_there, wiggle, squish_rate_func,
    lingering, exponential_decay
  Non-exported (use rate_functions.xxx):
    ease_in_sine, ease_out_sine, ease_in_out_sine,
    ease_in_quad, ease_out_quad, ease_in_out_quad,
    ease_in_cubic, ease_out_cubic, ease_in_out_cubic,
    ease_in_quart, ease_out_quart, ease_in_out_quart,
    ease_in_quint, ease_out_quint, ease_in_out_quint,
    ease_in_expo, ease_out_expo, ease_in_out_expo,
    ease_in_circ, ease_out_circ, ease_in_out_circ,
    ease_in_back, ease_out_back, ease_in_out_back,
    ease_in_elastic, ease_out_elastic, ease_in_out_elastic,
    ease_in_bounce, ease_out_bounce, ease_in_out_bounce

CAMERA/SCENE TYPES:
  - Scene               (standard 2D)
  - MovingCameraScene   (pan/zoom via self.camera.frame)
  - ZoomedScene         (picture-in-picture zoom)
  - ThreeDScene         (3D camera)
"""
