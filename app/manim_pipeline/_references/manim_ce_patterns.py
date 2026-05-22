"""
Manim Community Edition -- Comprehensive Code Pattern Reference
===============================================================

All patterns use `from manim import *` (Manim CE, NOT manimgl).
Verified against the installed Manim CE source at:
  .venv/lib/python3.11/site-packages/manim/

Table of Contents:
  1. GRAPH ANIMATIONS (Axes.plot, animated curves, area under curve)
  2. VALUETRACKER PATTERNS (morphing graphs, sweeping parameters, always_redraw)
  3. TRANSFORMMATCHINGTEX (equation step-through)
  4. NUMBERPLANE ANIMATIONS (coordinate transforms, vector fields)
  5. LAGGEDSTARTMAP PATTERNS (staggered reveals)
  6. PARAMETRIC CURVES (Lissajous, cardioid, spirals)
  7. RIEMANN SUMS & CALCULUS (definite integrals, secant/tangent)
  8. VARIABLE DISPLAY (DecimalNumber, Variable with ValueTracker)
  9. COMBINED PATTERNS (full scene examples mixing multiple techniques)
"""

from manim import *
import numpy as np


# =============================================================================
# 1. GRAPH ANIMATIONS
# =============================================================================

class BasicPlotting(Scene):
    """Plot a function on Axes using axes.plot()."""
    def construct(self):
        # Create axes
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-2, 8, 1],
            x_length=7,
            y_length=5,
            axis_config={"color": GREY_B, "stroke_width": 2},
            tips=True,
        )
        # Position axes (shift down to leave room for title)
        axes.shift(DOWN * 0.3)

        # Axis labels
        labels = axes.get_axis_labels(
            x_label=MathTex("x", font_size=28),
            y_label=MathTex("y", font_size=28),
        )

        # Plot functions
        quadratic = axes.plot(lambda x: x**2, color=BLUE, stroke_width=3)
        sine_curve = axes.plot(lambda x: 2 * np.sin(x), color=GREEN, stroke_width=3)

        # Graph labels
        quad_label = axes.get_graph_label(
            quadratic, label=MathTex("x^2"), x_val=2, direction=UL
        )
        sin_label = axes.get_graph_label(
            sine_curve, label=MathTex(r"2\sin(x)"), x_val=3, direction=DR
        )

        # Animate
        self.play(Create(axes), Write(labels), run_time=1.5)
        self.play(Create(quadratic), Write(quad_label), run_time=2)
        self.play(Create(sine_curve), Write(sin_label), run_time=2)
        self.wait(1)


class AnimatedCurveDrawing(Scene):
    """Animate a curve being drawn with a moving dot tracing it."""
    def construct(self):
        axes = Axes(
            x_range=[0, 2 * PI, PI / 4],
            y_range=[-1.5, 1.5, 0.5],
            x_length=8,
            y_length=4,
            axis_config={"color": GREY_B},
        )
        axes.shift(DOWN * 0.3)
        labels = axes.get_axis_labels(
            x_label=MathTex("t"), y_label=MathTex("f(t)")
        )

        # Create the curve
        curve = axes.plot(lambda x: np.sin(x), color=YELLOW, stroke_width=4)

        # Tracing dot using ValueTracker
        t = ValueTracker(0)
        dot = always_redraw(lambda: Dot(
            axes.c2p(t.get_value(), np.sin(t.get_value())),
            color=RED, radius=0.08,
        ))

        self.play(Create(axes), Write(labels), run_time=1)
        self.add(dot)
        self.play(
            Create(curve),
            t.animate.set_value(2 * PI),
            run_time=4,
            rate_func=linear,
        )
        self.wait(1)


class AreaUnderCurve(Scene):
    """Show the area under a curve using get_area() and get_riemann_rectangles()."""
    def construct(self):
        axes = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 6, 1],
            x_length=7,
            y_length=4.5,
            tips=False,
        )
        axes.shift(DOWN * 0.3)
        labels = axes.get_axis_labels(MathTex("x"), MathTex("y"))

        func = axes.plot(lambda x: 0.5 * x**2, color=BLUE, stroke_width=3)

        # Riemann rectangles with decreasing dx
        rects_coarse = axes.get_riemann_rectangles(
            func, x_range=[0, 4], dx=1.0,
            color=(TEAL, BLUE_B), fill_opacity=0.5,
        )
        rects_fine = axes.get_riemann_rectangles(
            func, x_range=[0, 4], dx=0.25,
            color=(TEAL, BLUE_B), fill_opacity=0.5,
        )

        # Smooth area
        area = axes.get_area(func, x_range=(0, 4), color=(BLUE_B, GREEN_B), opacity=0.5)

        self.play(Create(axes), Write(labels), run_time=1)
        self.play(Create(func), run_time=1.5)

        # Show progression: coarse -> fine -> smooth
        self.play(Create(rects_coarse), run_time=1)
        self.wait(0.5)
        self.play(ReplacementTransform(rects_coarse, rects_fine), run_time=1.5)
        self.wait(0.5)
        self.play(ReplacementTransform(rects_fine, area), run_time=1.5)
        self.wait(1)


class MultipleFunctionsOnAxes(Scene):
    """Plot multiple functions with a color-coded legend."""
    def construct(self):
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-1, 4, 1],
            x_length=7,
            y_length=3.5,
            axis_config={"color": GREY_B},
        )
        axes.shift(DOWN * 0.4)

        relu = axes.plot(
            lambda x: np.maximum(0, x), color=GREEN, stroke_width=4
        )
        sigmoid_plot = axes.plot(
            lambda x: 1 / (1 + np.exp(-x)), color=ORANGE, stroke_width=4
        )
        tanh_plot = axes.plot(
            lambda x: np.tanh(x), color=PURPLE, stroke_width=4
        )

        relu_label = MathTex(r"\text{ReLU}", color=GREEN, font_size=28)
        sig_label = MathTex(r"\sigma(x)", color=ORANGE, font_size=28)
        tanh_label = MathTex(r"\tanh(x)", color=PURPLE, font_size=28)

        legend = VGroup(relu_label, sig_label, tanh_label).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        legend.to_corner(UR, buff=0.5)

        self.play(Create(axes), run_time=1)
        self.play(Create(relu), Write(relu_label), run_time=1.5)
        self.play(Create(sigmoid_plot), Write(sig_label), run_time=1.5)
        self.play(Create(tanh_plot), Write(tanh_label), run_time=1.5)
        self.wait(1)


# =============================================================================
# 2. VALUETRACKER PATTERNS
# =============================================================================

class MorphingGraph(Scene):
    """Use ValueTracker + always_redraw to morph a graph's parameter in real time."""
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=7,
            y_length=3.5,
            axis_config={"color": GREY_B},
        )
        axes.shift(DOWN * 0.4)
        labels = axes.get_axis_labels(MathTex("x"), MathTex("y"))

        # ValueTracker for the frequency parameter
        k = ValueTracker(1)

        # always_redraw: the graph rebuilds every frame as k changes
        graph = always_redraw(
            lambda: axes.plot(
                lambda x: np.sin(k.get_value() * x),
                color=YELLOW,
                stroke_width=4,
            )
        )

        # Display current k value
        k_label = always_redraw(
            lambda: MathTex(
                f"k = {k.get_value():.2f}",
                font_size=32,
                color=YELLOW,
            ).to_corner(UR, buff=0.5)
        )

        formula = MathTex(r"y = \sin(kx)", font_size=36, color=WHITE)
        formula.shift(UP * 2.5)

        self.play(Create(axes), Write(labels), Write(formula), run_time=1.5)
        self.add(graph, k_label)

        # Sweep k from 1 to 5
        self.play(k.animate.set_value(5), run_time=4, rate_func=smooth)
        # Sweep back
        self.play(k.animate.set_value(0.5), run_time=3, rate_func=smooth)
        self.wait(1)


class SweepingDotOnCurve(Scene):
    """A dot sweeps along a curve with a tracking label showing coordinates."""
    def construct(self):
        axes = Axes(
            x_range=[-4, 4, 1],
            y_range=[-1, 4, 1],
            x_length=7,
            y_length=3.5,
        )
        axes.shift(DOWN * 0.4)

        curve = axes.plot(lambda x: np.maximum(0, x), color=GREEN, stroke_width=4)

        x_val = ValueTracker(-4)

        dot = always_redraw(lambda: Dot(
            axes.c2p(x_val.get_value(), np.maximum(0, x_val.get_value())),
            color=YELLOW, radius=0.1,
        ))

        # Coordinates label that follows the dot
        coord_label = always_redraw(lambda: MathTex(
            f"({x_val.get_value():.1f},\\, {np.maximum(0, x_val.get_value()):.1f})",
            font_size=22, color=YELLOW,
        ).next_to(dot, UR, buff=0.15))

        # Vertical dashed line from x-axis to dot
        v_line = always_redraw(lambda: DashedLine(
            axes.c2p(x_val.get_value(), 0),
            axes.c2p(x_val.get_value(), np.maximum(0, x_val.get_value())),
            color=GREY_B, stroke_width=1, dash_length=0.05,
        ))

        self.play(Create(axes), Create(curve), run_time=1.5)
        self.add(dot, coord_label, v_line)
        self.play(x_val.animate.set_value(4), run_time=5, rate_func=linear)
        self.wait(1)


class TwoTrackersMorphTwoGraphs(Scene):
    """Use two independent ValueTrackers to morph amplitude and frequency."""
    def construct(self):
        axes = Axes(
            x_range=[0, 2 * PI, PI / 2],
            y_range=[-3, 3, 1],
            x_length=8,
            y_length=4,
            axis_config={"color": GREY_B},
        )
        axes.shift(DOWN * 0.3)

        amp = ValueTracker(1)
        freq = ValueTracker(1)

        graph = always_redraw(
            lambda: axes.plot(
                lambda x: amp.get_value() * np.sin(freq.get_value() * x),
                color=BLUE,
                stroke_width=4,
            )
        )

        amp_label = always_redraw(
            lambda: MathTex(
                f"A = {amp.get_value():.1f}",
                font_size=28, color=RED,
            ).to_corner(UR, buff=0.5)
        )
        freq_label = always_redraw(
            lambda: MathTex(
                f"\\omega = {freq.get_value():.1f}",
                font_size=28, color=GREEN,
            ).next_to(amp_label, DOWN, buff=0.2)
        )

        title = MathTex(r"y = A\sin(\omega x)", font_size=36).shift(UP * 3)

        self.play(Create(axes), Write(title), run_time=1)
        self.add(graph, amp_label, freq_label)

        # Animate amplitude change
        self.play(amp.animate.set_value(2.5), run_time=2)
        # Animate frequency change
        self.play(freq.animate.set_value(3), run_time=2)
        # Both simultaneously
        self.play(
            amp.animate.set_value(1),
            freq.animate.set_value(1),
            run_time=2,
        )
        self.wait(1)


class ValueTrackerWithDecimalDisplay(Scene):
    """Use Variable mobject for automatic decimal display linked to a ValueTracker."""
    def construct(self):
        # Variable auto-creates its own ValueTracker and displays label = value
        x_var = Variable(2.0, "x", num_decimal_places=3)
        x_squared_var = Variable(4.0, "x^2", num_decimal_places=3)

        Group(x_var, x_squared_var).arrange(DOWN, buff=0.5).to_edge(LEFT, buff=1)

        # Link x^2 to x via updater
        x_squared_var.add_updater(
            lambda v: v.tracker.set_value(x_var.tracker.get_value() ** 2)
        )

        x_var.label.set_color(RED)
        x_var.value.set_color(RED)
        x_squared_var.label.set_color(BLUE)
        x_squared_var.value.set_color(BLUE)

        self.play(Write(x_var), Write(x_squared_var))
        self.play(x_var.tracker.animate.set_value(5), run_time=3, rate_func=linear)
        self.play(x_var.tracker.animate.set_value(-2), run_time=2, rate_func=linear)
        self.wait(1)


# =============================================================================
# 3. TRANSFORMMATCHINGTEX (Equation Step-Through)
# =============================================================================

class EquationStepThrough(Scene):
    """Step through algebraic manipulations using TransformMatchingTex.

    KEY RULE: Use double-brace {{ }} around each "part" you want to match
    between equations. Parts with the same tex_string get smoothly transformed.
    """
    def construct(self):
        # Step 1: Starting equation
        eq1 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")
        eq1.shift(UP * 0.5)

        # Step 2: Rearrange
        eq2 = MathTex("{{a}}^2", "=", "{{c}}^2", "-", "{{b}}^2")
        eq2.shift(UP * 0.5)

        # Step 3: Take square root
        eq3 = MathTex("{{a}}", "=", r"\sqrt{", "{{c}}^2", "-", "{{b}}^2", "}")
        eq3.shift(UP * 0.5)

        title = Text("Pythagorean Theorem", font_size=40, color=WHITE)
        title.to_edge(UP, buff=0.5)

        self.play(Write(title))
        self.play(Write(eq1), run_time=1.5)
        self.wait(1)

        # Transform: matching parts ({a}^2, {b}^2, {c}^2, =) stay, others fade
        self.play(TransformMatchingTex(eq1, eq2), run_time=1.5)
        self.wait(1)

        self.play(TransformMatchingTex(eq2, eq3), run_time=1.5)
        self.wait(1)


class QuadraticFormulaDerivation(Scene):
    """Derive the quadratic formula step by step with TransformMatchingTex."""
    def construct(self):
        # Each step uses {{ }} braces to mark the matchable parts
        step1 = MathTex(
            "{{a}}", "{{x}}^2", "+", "{{b}}", "{{x}}", "+", "{{c}}", "=", "0"
        )
        step2 = MathTex(
            "{{x}}^2", "+", r"\frac{{{b}}}{{{a}}}", "{{x}}", "=",
            r"-\frac{{{c}}}{{{a}}}"
        )
        step3 = MathTex(
            "{{x}}", "=",
            r"\frac{-{{b}} \pm \sqrt{{{b}}^2 - 4{{a}}{{c}}}}{2{{a}}}"
        )

        for eq in [step1, step2, step3]:
            eq.move_to(ORIGIN)

        self.play(Write(step1), run_time=1.5)
        self.wait(1)
        self.play(TransformMatchingTex(step1, step2), run_time=2)
        self.wait(1)
        self.play(TransformMatchingTex(step2, step3), run_time=2)
        self.wait(2)


class TransformMatchingTexWithKeyMap(Scene):
    """Use key_map to specify non-obvious correspondences between parts.

    key_map lets you say: 'even though the tex strings are different,
    transform THIS part into THAT part.'
    """
    def construct(self):
        eq1 = MathTex("{{x}}^2", "+", "{{y}}^2", "=", "{{z}}^2")
        eq2 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")

        eq1.move_to(ORIGIN)
        eq2.move_to(ORIGIN)

        self.play(Write(eq1))
        self.wait(0.5)

        # key_map: x -> a, y -> b, z -> c (since the tex_strings differ)
        self.play(
            TransformMatchingTex(
                eq1, eq2,
                key_map={"x": "a", "y": "b", "z": "c"},
            ),
            run_time=2,
        )
        self.wait(1)


# =============================================================================
# 4. NUMBERPLANE ANIMATIONS
# =============================================================================

class NumberPlaneBasic(Scene):
    """Create a NumberPlane with styled background lines."""
    def construct(self):
        plane = NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-4, 4, 1],
            background_line_style={
                "stroke_color": TEAL,
                "stroke_width": 2,
                "stroke_opacity": 0.4,
            },
        )
        self.play(Create(plane), run_time=2)
        self.wait(1)


class NonlinearTransformOnPlane(Scene):
    """Apply a nonlinear function to a NumberPlane (complex mapping, warping space)."""
    def construct(self):
        plane = NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
        )

        # IMPORTANT: must call prepare_for_nonlinear_transform before apply_function
        plane.prepare_for_nonlinear_transform(num_inserted_curves=50)

        title = Text("z -> z^2 mapping", font_size=32, color=WHITE).to_edge(UP)

        self.play(Create(plane), Write(title), run_time=2)
        self.wait(1)

        # Apply complex squaring: (x+iy) -> (x^2 - y^2, 2xy)
        self.play(
            plane.animate.apply_function(
                lambda p: np.array([
                    p[0]**2 - p[1]**2,
                    2 * p[0] * p[1],
                    0,
                ])
            ),
            run_time=3,
        )
        self.wait(2)


class VectorFieldOnPlane(Scene):
    """Display an ArrowVectorField on top of a coordinate system."""
    def construct(self):
        plane = NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-4, 4, 1],
            background_line_style={"stroke_opacity": 0.3},
        )

        # Vector field function: takes position array, returns velocity array
        vf = ArrowVectorField(
            lambda pos: np.array([
                np.sin(pos[1]),
                np.cos(pos[0]),
                0,
            ]),
            x_range=[-5, 5, 1],
            y_range=[-4, 4, 1],
        )

        title = MathTex(
            r"\vec{F}(x,y) = (\sin y,\, \cos x)",
            font_size=32, color=WHITE,
        ).to_edge(UP)

        self.play(Create(plane), run_time=1)
        self.play(Write(title), run_time=0.5)
        self.play(Create(vf), run_time=2)
        self.wait(2)


class StreamLinesAnimation(Scene):
    """Animate StreamLines flowing through a vector field."""
    def construct(self):
        plane = NumberPlane(
            background_line_style={"stroke_opacity": 0.2},
        )

        stream = StreamLines(
            lambda pos: np.array([
                -pos[1],
                pos[0],
                0,
            ]),
            x_range=[-4, 4, 0.5],
            y_range=[-3, 3, 0.5],
            stroke_width=2,
            max_anchors_per_line=30,
        )

        self.add(plane)
        # StreamLines have a special start_animation() method
        stream.start_animation(warm_up=True, flow_speed=1.5)
        self.add(stream)
        self.wait(4)
        stream.end_animation()
        self.wait(1)


class LinearTransformationOnPlane(Scene):
    """Apply a linear (matrix) transformation to a NumberPlane with animated vectors."""
    def construct(self):
        plane = NumberPlane(
            x_range=[-4, 4, 1],
            y_range=[-4, 4, 1],
            background_line_style={"stroke_opacity": 0.4},
        )

        # Draw basis vectors
        i_hat = plane.get_vector([1, 0], color=GREEN)
        j_hat = plane.get_vector([0, 1], color=RED)

        i_label = MathTex(r"\hat{i}", color=GREEN, font_size=28).next_to(i_hat, DOWN)
        j_label = MathTex(r"\hat{j}", color=RED, font_size=28).next_to(j_hat, LEFT)

        matrix = MathTex(
            r"\begin{bmatrix} 2 & 1 \\ 1 & 2 \end{bmatrix}",
            font_size=32,
        ).to_corner(UL, buff=0.5)

        self.play(Create(plane), run_time=1)
        self.play(Create(i_hat), Create(j_hat), Write(i_label), Write(j_label))
        self.play(Write(matrix))
        self.wait(0.5)

        # Apply the matrix transformation
        self.play(
            plane.animate.apply_matrix([[2, 1], [1, 2]]),
            i_hat.animate.apply_matrix([[2, 1], [1, 2]]),
            j_hat.animate.apply_matrix([[2, 1], [1, 2]]),
            run_time=3,
        )
        self.wait(2)


# =============================================================================
# 5. LAGGEDSTARTMAP PATTERNS
# =============================================================================

class LaggedStartMapFadeIn(Scene):
    """Use LaggedStartMap for a staggered reveal of multiple objects."""
    def construct(self):
        # Create a grid of dots
        dots = VGroup(
            *[Dot(radius=0.15, color=BLUE) for _ in range(35)]
        ).arrange_in_grid(rows=5, cols=7, buff=MED_LARGE_BUFF)

        title = Text("LaggedStartMap - Staggered FadeIn", font_size=30)
        title.to_edge(UP, buff=0.5)

        self.play(Write(title))

        # Staggered FadeIn: each dot fades in slightly after the previous
        self.play(
            LaggedStartMap(FadeIn, dots, lag_ratio=0.1, run_time=3)
        )
        self.wait(1)

        # Staggered scale up with GrowFromCenter
        self.play(
            LaggedStartMap(
                FadeOut, dots,
                lag_ratio=0.05,
                run_time=2,
            )
        )
        self.wait(0.5)


class LaggedStartMapWithCreate(Scene):
    """Staggered Create animation for a list of math expressions."""
    def construct(self):
        equations = VGroup(
            MathTex(r"e^{i\pi} + 1 = 0"),
            MathTex(r"E = mc^2"),
            MathTex(r"\nabla \cdot \vec{E} = \frac{\rho}{\varepsilon_0}"),
            MathTex(r"F = ma"),
            MathTex(r"\oint \vec{B} \cdot d\vec{l} = \mu_0 I"),
        )
        equations.arrange(DOWN, buff=0.5, aligned_edge=LEFT)
        equations.to_edge(LEFT, buff=1)

        self.play(
            LaggedStartMap(Write, equations, lag_ratio=0.3, run_time=5)
        )
        self.wait(2)


class LaggedStartMapCircularReveal(Scene):
    """Staggered reveal in a circular pattern."""
    def construct(self):
        circles = VGroup(
            *[
                Circle(radius=0.3, color=color, fill_opacity=0.8)
                for color in [RED, ORANGE, YELLOW, GREEN, TEAL, BLUE, PURPLE, PINK]
            ]
        )
        circles.arrange_in_grid(rows=2, cols=4, buff=0.8)

        labels = VGroup(
            *[
                Text(name, font_size=18, color=WHITE)
                for name in ["Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink"]
            ]
        )
        for label, circle in zip(labels, circles):
            label.next_to(circle, DOWN, buff=0.15)

        group = VGroup(*[VGroup(c, l) for c, l in zip(circles, labels)])

        self.play(
            LaggedStartMap(
                FadeIn, group,
                shift=UP * 0.5,
                lag_ratio=0.15,
                run_time=3,
            )
        )
        self.wait(1)

        # Staggered exit
        self.play(
            LaggedStartMap(
                FadeOut, group,
                shift=DOWN * 0.5,
                lag_ratio=0.1,
                run_time=2,
            )
        )


class LaggedStartWithCustomAnimations(Scene):
    """LaggedStart (not Map) for manually specified animations with stagger."""
    def construct(self):
        squares = VGroup(
            *[Square(side_length=0.8, color=BLUE, fill_opacity=0.5) for _ in range(5)]
        )
        squares.arrange(RIGHT, buff=0.5)

        self.play(
            LaggedStart(
                *[FadeIn(sq, shift=UP * 0.5) for sq in squares],
                lag_ratio=0.25,
                run_time=3,
            )
        )
        self.wait(0.5)

        # Staggered color change
        self.play(
            LaggedStart(
                *[sq.animate.set_color(YELLOW) for sq in squares],
                lag_ratio=0.2,
                run_time=2,
            )
        )
        self.wait(1)


# =============================================================================
# 6. PARAMETRIC CURVES
# =============================================================================

class ParametricCurveExamples(Scene):
    """Plot parametric curves on Axes using plot_parametric_curve."""
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=6,
            y_length=6,
            axis_config={"color": GREY_B},
        )

        # Cardioid: r = 1 - cos(theta) in parametric form
        cardioid = axes.plot_parametric_curve(
            lambda t: np.array([
                (1 - np.cos(t)) * np.cos(t),
                (1 - np.cos(t)) * np.sin(t),
                0,
            ]),
            t_range=[0, 2 * PI],
            color=RED,
            stroke_width=3,
        )

        # Lissajous figure
        lissajous = axes.plot_parametric_curve(
            lambda t: np.array([
                2 * np.sin(3 * t),
                2 * np.sin(2 * t),
                0,
            ]),
            t_range=[0, 2 * PI],
            color=YELLOW,
            stroke_width=3,
        )

        title1 = MathTex(r"\text{Cardioid}", font_size=28, color=RED).to_corner(UL)
        title2 = MathTex(r"\text{Lissajous}", font_size=28, color=YELLOW).to_corner(UL)

        self.play(Create(axes), run_time=1)
        self.play(Write(title1), Create(cardioid), run_time=3)
        self.wait(1)
        self.play(
            FadeOut(cardioid), FadeOut(title1),
            Write(title2), Create(lissajous),
            run_time=3,
        )
        self.wait(1)


class AnimatedParametricWithTracker(Scene):
    """Animate a parametric curve being drawn using ValueTracker for the parameter."""
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            x_length=7,
            y_length=4,
        )
        axes.shift(DOWN * 0.3)

        # Spiral parametric: x = t*cos(t), y = t*sin(t) (scaled)
        t_max = ValueTracker(0.01)

        spiral = always_redraw(
            lambda: axes.plot_parametric_curve(
                lambda t: np.array([
                    0.3 * t * np.cos(t),
                    0.3 * t * np.sin(t),
                    0,
                ]),
                t_range=[0, t_max.get_value()],
                color=TEAL,
                stroke_width=3,
            )
        )

        # Moving tip dot
        tip_dot = always_redraw(lambda: Dot(
            axes.c2p(
                0.3 * t_max.get_value() * np.cos(t_max.get_value()),
                0.3 * t_max.get_value() * np.sin(t_max.get_value()),
            ),
            color=YELLOW, radius=0.06,
        ))

        self.play(Create(axes), run_time=1)
        self.add(spiral, tip_dot)
        self.play(t_max.animate.set_value(6 * PI), run_time=6, rate_func=linear)
        self.wait(1)


# =============================================================================
# 7. RIEMANN SUMS & CALCULUS ANIMATIONS
# =============================================================================

class RiemannSumConvergence(Scene):
    """Animate Riemann rectangles becoming finer to show integral convergence."""
    def construct(self):
        axes = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 6, 1],
            x_length=7,
            y_length=4,
            tips=False,
        )
        axes.shift(DOWN * 0.3)

        func = axes.plot(lambda x: 0.25 * x**2 + 0.5, color=BLUE, stroke_width=3)

        title = MathTex(
            r"\int_0^4 \left(\tfrac{x^2}{4} + \tfrac{1}{2}\right)\,dx",
            font_size=36,
        ).shift(UP * 2.8)

        self.play(Create(axes), Create(func), Write(title), run_time=1.5)

        # Progressive refinement
        dx_values = [1.0, 0.5, 0.25, 0.1]
        prev_rects = None

        for dx in dx_values:
            new_rects = axes.get_riemann_rectangles(
                func,
                x_range=[0, 4],
                dx=dx,
                color=(TEAL, BLUE_B),
                fill_opacity=0.5,
                stroke_width=0.5,
            )
            if prev_rects is None:
                self.play(Create(new_rects), run_time=1)
            else:
                self.play(ReplacementTransform(prev_rects, new_rects), run_time=1)
            self.wait(0.5)
            prev_rects = new_rects

        # Final: smooth area
        area = axes.get_area(func, x_range=(0, 4), color=(TEAL, GREEN), opacity=0.4)
        self.play(ReplacementTransform(prev_rects, area), run_time=1)
        self.wait(1)


class SecantToTangent(Scene):
    """Animate a secant line converging to a tangent using ValueTracker for dx."""
    def construct(self):
        axes = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 7, 1],
            x_length=7,
            y_length=4.5,
        )
        axes.shift(DOWN * 0.3)

        func = axes.plot(lambda x: 0.25 * x**2, color=BLUE, stroke_width=3)

        x_point = 2.0
        dx = ValueTracker(2.0)

        # Secant slope group (rebuilt each frame as dx changes)
        secant_group = always_redraw(
            lambda: axes.get_secant_slope_group(
                x=x_point,
                graph=func,
                dx=dx.get_value(),
                dx_line_color=GREEN,
                secant_line_color=RED,
                secant_line_length=6,
            )
        )

        dx_label = always_redraw(
            lambda: MathTex(
                f"\\Delta x = {dx.get_value():.2f}",
                font_size=28,
                color=GREEN,
            ).to_corner(UR, buff=0.5)
        )

        title = MathTex(r"f(x) = \frac{x^2}{4}", font_size=32).shift(UP * 2.8)

        self.play(Create(axes), Create(func), Write(title), run_time=1.5)
        self.add(secant_group, dx_label)

        # dx shrinks: secant -> tangent
        self.play(dx.animate.set_value(0.01), run_time=5, rate_func=smooth)
        self.wait(2)


# =============================================================================
# 8. VARIABLE DISPLAY (DecimalNumber, Integer, Variable)
# =============================================================================

class DecimalNumberUpdater(Scene):
    """Use DecimalNumber with add_updater to show a value changing in real time."""
    def construct(self):
        tracker = ValueTracker(0)

        # DecimalNumber with custom formatting
        num = DecimalNumber(
            0, num_decimal_places=2, font_size=48, color=YELLOW,
        )
        num.add_updater(lambda n: n.set_value(tracker.get_value()))

        label = Text("Value: ", font_size=36, color=WHITE)
        group = VGroup(label, num).arrange(RIGHT, buff=0.3)
        group.move_to(ORIGIN)

        # Keep the label + number grouped and centered
        num.add_updater(lambda n: n.next_to(label, RIGHT, buff=0.3))

        self.play(Write(group), run_time=0.5)
        self.play(tracker.animate.set_value(42.17), run_time=3, rate_func=smooth)
        self.play(tracker.animate.set_value(-5.5), run_time=2, rate_func=smooth)
        self.wait(1)


# =============================================================================
# 9. COMBINED PATTERNS -- Full Scene Examples
# =============================================================================

class DerivativeVisualization(Scene):
    """Complete scene: function plot + tangent line + derivative plot + ValueTracker."""
    def construct(self):
        # -- Title --
        title = Text("Derivative Visualization", font_size=40, color=WHITE)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=0.8)

        # -- Function axes --
        axes = Axes(
            x_range=[-2, 4, 1],
            y_range=[-2, 10, 2],
            x_length=5,
            y_length=3.5,
            axis_config={"color": GREY_B, "stroke_width": 2},
            tips=False,
        )
        axes.to_edge(LEFT, buff=1).shift(DOWN * 0.5)

        f_label = MathTex(r"f(x) = x^2", font_size=24, color=BLUE)
        f_label.next_to(axes, UP, buff=0.2)

        func = axes.plot(lambda x: x**2, color=BLUE, stroke_width=3)

        # -- Derivative axes --
        d_axes = Axes(
            x_range=[-2, 4, 1],
            y_range=[-4, 8, 2],
            x_length=5,
            y_length=3.5,
            axis_config={"color": GREY_B, "stroke_width": 2},
            tips=False,
        )
        d_axes.to_edge(RIGHT, buff=1).shift(DOWN * 0.5)

        df_label = MathTex(r"f'(x) = 2x", font_size=24, color=GREEN)
        df_label.next_to(d_axes, UP, buff=0.2)

        deriv = d_axes.plot(lambda x: 2 * x, color=GREEN, stroke_width=3)

        self.play(
            Create(axes), Write(f_label), Create(func),
            Create(d_axes), Write(df_label), Create(deriv),
            run_time=2,
        )

        # -- Sweeping tangent on f(x) --
        x_tracker = ValueTracker(-2)

        # Tangent line on f(x)
        tangent_line = always_redraw(lambda: axes.get_secant_slope_group(
            x=x_tracker.get_value(),
            graph=func,
            dx=0.01,
            secant_line_color=YELLOW,
            secant_line_length=3,
        ))

        # Dot on f(x)
        f_dot = always_redraw(lambda: Dot(
            axes.c2p(x_tracker.get_value(), x_tracker.get_value()**2),
            color=YELLOW, radius=0.06,
        ))

        # Dot on f'(x) showing the slope value
        df_dot = always_redraw(lambda: Dot(
            d_axes.c2p(x_tracker.get_value(), 2 * x_tracker.get_value()),
            color=YELLOW, radius=0.06,
        ))

        # Slope label
        slope_label = always_redraw(lambda: MathTex(
            f"\\text{{slope}} = {2 * x_tracker.get_value():.1f}",
            font_size=22, color=YELLOW,
        ).next_to(f_dot, UR, buff=0.15))

        self.add(tangent_line, f_dot, df_dot, slope_label)
        self.play(
            x_tracker.animate.set_value(4),
            run_time=6,
            rate_func=linear,
        )
        self.wait(1)


class FourierSeriesApproximation(Scene):
    """Progressively add Fourier terms to approximate a square wave."""
    def construct(self):
        axes = Axes(
            x_range=[-PI, PI, PI / 2],
            y_range=[-1.5, 1.5, 0.5],
            x_length=8,
            y_length=4,
            axis_config={"color": GREY_B},
        )
        axes.shift(DOWN * 0.3)

        title = MathTex(
            r"\text{Fourier Series: Square Wave}",
            font_size=32,
        ).shift(UP * 3)

        def square_wave_approx(x, n_terms):
            """Sum of first n_terms of Fourier series for square wave."""
            result = 0
            for k in range(1, 2 * n_terms, 2):  # odd harmonics only
                result += (4 / (PI * k)) * np.sin(k * x)
            return result

        self.play(Create(axes), Write(title), run_time=1)

        n_tracker = ValueTracker(1)
        prev_graph = None

        for n in [1, 2, 3, 5, 10, 25]:
            graph = axes.plot(
                lambda x, n=n: square_wave_approx(x, n),
                color=YELLOW,
                stroke_width=3,
            )
            n_label = MathTex(f"n = {n}", font_size=28, color=YELLOW)
            n_label.to_corner(UR, buff=0.5)

            if prev_graph is None:
                self.play(Create(graph), Write(n_label), run_time=1)
            else:
                self.play(
                    ReplacementTransform(prev_graph, graph),
                    ReplacementTransform(prev_n_label, n_label),
                    run_time=1,
                )
            self.wait(0.5)
            prev_graph = graph
            prev_n_label = n_label

        self.wait(2)


class GradientDescentVisualization(Scene):
    """Animate gradient descent on a 1D loss function using ValueTracker."""
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[0, 10, 2],
            x_length=7,
            y_length=4,
            axis_config={"color": GREY_B},
        )
        axes.shift(DOWN * 0.3)

        labels = axes.get_axis_labels(
            x_label=MathTex(r"\theta", font_size=28),
            y_label=MathTex(r"L(\theta)", font_size=28),
        )

        # Loss function: x^2 (convex)
        loss = axes.plot(lambda x: x**2, color=BLUE, stroke_width=3)

        title = MathTex(r"\text{Gradient Descent: } L(\theta) = \theta^2", font_size=28)
        title.shift(UP * 2.8)

        self.play(Create(axes), Write(labels), Write(title), Create(loss), run_time=1.5)

        # Gradient descent steps
        x_pos = ValueTracker(2.5)
        lr = 0.3

        dot = always_redraw(lambda: Dot(
            axes.c2p(x_pos.get_value(), x_pos.get_value()**2),
            color=RED, radius=0.1,
        ))

        val_label = always_redraw(lambda: MathTex(
            f"\\theta = {x_pos.get_value():.2f}",
            font_size=24, color=RED,
        ).next_to(dot, UR, buff=0.15))

        self.add(dot, val_label)

        # Perform gradient descent steps
        for step in range(8):
            current_x = x_pos.get_value()
            gradient = 2 * current_x  # d/dx(x^2) = 2x
            new_x = current_x - lr * gradient
            self.play(x_pos.animate.set_value(new_x), run_time=0.6)
            self.wait(0.2)

        self.wait(1)


class CompleteAnimationShowcase(Scene):
    """A complete scene that combines: MathTex, Axes, ValueTracker, TransformMatchingTex,
    LaggedStartMap, and area/Riemann patterns into one flowing animation.
    """
    def construct(self):
        # === Section 1: Title + Equation ===
        title = Text("Calculus in Motion", font_size=44, weight="BOLD", color=WHITE)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title, shift=UP * 0.3), run_time=0.8)

        # Equation step-through
        eq1 = MathTex(r"\int_0^1", "{{x}}^2", r"\,dx")
        eq2 = MathTex(r"=", r"\left[\frac{{{x}}^3}{3}\right]_0^1")
        eq3 = MathTex(r"=", r"\frac{1}{3}", "-", r"\frac{0}{3}")
        eq4 = MathTex(r"=", r"\frac{1}{3}")

        for eq in [eq1, eq2, eq3, eq4]:
            eq.shift(UP * 1.5)

        self.play(Write(eq1), run_time=1.5)
        self.wait(0.5)
        self.play(TransformMatchingTex(eq1, eq2), run_time=1.5)
        self.wait(0.5)
        self.play(TransformMatchingTex(eq2, eq3), run_time=1)
        self.wait(0.5)
        self.play(TransformMatchingTex(eq3, eq4), run_time=1)
        self.wait(0.5)

        # === Section 2: Graph with area ===
        axes = Axes(
            x_range=[0, 1.5, 0.5],
            y_range=[0, 1.5, 0.5],
            x_length=5,
            y_length=3,
            axis_config={"color": GREY_B},
            tips=False,
        )
        axes.shift(DOWN * 1.0)

        curve = axes.plot(lambda x: x**2, color=BLUE, stroke_width=3)
        area = axes.get_area(curve, x_range=(0, 1), color=(TEAL, BLUE), opacity=0.5)

        result_label = MathTex(
            r"\text{Area} = \frac{1}{3}",
            font_size=24, color=TEAL,
        ).next_to(area, RIGHT, buff=0.5)

        self.play(
            FadeOut(eq4),
            Create(axes),
            Create(curve),
            run_time=1.5,
        )
        self.play(FadeIn(area), Write(result_label), run_time=1)
        self.wait(0.5)

        # === Section 3: ValueTracker sweep ===
        t = ValueTracker(0)
        sweep_area = always_redraw(
            lambda: axes.get_area(
                curve,
                x_range=(0, np.clip(t.get_value(), 0.001, 1.5)),
                color=YELLOW,
                opacity=0.3,
            )
        )
        sweep_dot = always_redraw(lambda: Dot(
            axes.c2p(t.get_value(), t.get_value()**2),
            color=YELLOW, radius=0.06,
        ))

        self.play(FadeOut(area), FadeOut(result_label))
        self.add(sweep_area, sweep_dot)
        self.play(t.animate.set_value(1.0), run_time=3, rate_func=linear)
        self.wait(0.5)

        # === Section 4: LaggedStart cleanup ===
        all_objects = VGroup(axes, curve, sweep_area, sweep_dot, title)
        self.play(
            LaggedStart(
                *[FadeOut(obj, shift=DOWN * 0.3) for obj in all_objects],
                lag_ratio=0.15,
                run_time=2,
            )
        )
        self.wait(0.5)

        # Outro
        outro = Text("Octoflash", font_size=36, color=TEAL, weight="BOLD")
        self.play(FadeIn(outro, shift=UP * 0.3), run_time=0.8)
        self.wait(1)
        self.play(FadeOut(outro), run_time=0.5)


# =============================================================================
# QUICK-REFERENCE CHEAT SHEET (comments only, for fast copy-paste)
# =============================================================================

# --- Axes creation ---
# axes = Axes(x_range=[-4, 4, 1], y_range=[-2, 8, 1], x_length=7, y_length=4,
#             axis_config={"color": GREY_B, "stroke_width": 2}, tips=True)
# labels = axes.get_axis_labels(MathTex("x"), MathTex("y"))

# --- Plotting ---
# graph = axes.plot(lambda x: np.sin(x), color=BLUE, stroke_width=3)
# graph = axes.plot(lambda x: np.maximum(0, x), color=GREEN)  # ReLU
# graph = axes.plot(log_func, x_range=(0.001, 6, 0.001), color=RED)

# --- Parametric curves ---
# curve = axes.plot_parametric_curve(
#     lambda t: np.array([np.cos(t), np.sin(t), 0]),
#     t_range=[0, 2*PI], color=RED,
# )

# --- Graph label ---
# label = axes.get_graph_label(graph, label=MathTex(r"\sin(x)"), x_val=PI/2, direction=UR)

# --- Area under curve ---
# area = axes.get_area(graph, x_range=(0, PI), color=(BLUE, GREEN), opacity=0.4)

# --- Riemann rectangles ---
# rects = axes.get_riemann_rectangles(graph, x_range=[0, 4], dx=0.25,
#                                      color=(TEAL, BLUE_B), fill_opacity=0.5)

# --- Secant slope group ---
# secant = axes.get_secant_slope_group(x=2.0, graph=graph, dx=1.0,
#                                       dx_line_color=GREEN, secant_line_color=RED)

# --- ValueTracker + always_redraw ---
# k = ValueTracker(1)
# graph = always_redraw(lambda: axes.plot(lambda x: np.sin(k.get_value() * x), color=BLUE))
# self.play(k.animate.set_value(5), run_time=3, rate_func=linear)

# --- Dot on curve ---
# x_val = ValueTracker(-4)
# dot = always_redraw(lambda: Dot(
#     axes.c2p(x_val.get_value(), func(x_val.get_value())),
#     color=YELLOW, radius=0.08
# ))

# --- TransformMatchingTex ---
# eq1 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2")
# eq2 = MathTex("{{a}}^2", "=", "{{c}}^2", "-", "{{b}}^2")
# self.play(TransformMatchingTex(eq1, eq2), run_time=1.5)
# With key_map: TransformMatchingTex(eq1, eq2, key_map={"x": "a"})

# --- NumberPlane ---
# plane = NumberPlane(x_range=[-5, 5, 1], y_range=[-4, 4, 1],
#                     background_line_style={"stroke_color": TEAL, "stroke_opacity": 0.4})

# --- Nonlinear transform ---
# plane.prepare_for_nonlinear_transform(num_inserted_curves=50)
# self.play(plane.animate.apply_function(lambda p: np.array([p[0]**2-p[1]**2, 2*p[0]*p[1], 0])))

# --- Linear transform ---
# self.play(plane.animate.apply_matrix([[2, 1], [1, 2]]))

# --- ArrowVectorField ---
# vf = ArrowVectorField(lambda pos: np.array([np.sin(pos[1]), np.cos(pos[0]), 0]),
#                        x_range=[-5, 5, 1], y_range=[-4, 4, 1])

# --- StreamLines ---
# stream = StreamLines(func, x_range=[-4, 4, 0.5], y_range=[-3, 3, 0.5])
# stream.start_animation(warm_up=True, flow_speed=1.5)

# --- LaggedStartMap ---
# self.play(LaggedStartMap(FadeIn, vgroup, lag_ratio=0.1, run_time=3))
# self.play(LaggedStartMap(Write, equations, lag_ratio=0.3, run_time=5))

# --- LaggedStart (manual) ---
# self.play(LaggedStart(*[FadeIn(obj) for obj in objects], lag_ratio=0.2, run_time=2))

# --- Variable display ---
# x_var = Variable(2.0, "x", num_decimal_places=3)
# self.play(x_var.tracker.animate.set_value(5), run_time=2)

# --- DecimalNumber ---
# num = DecimalNumber(0, num_decimal_places=2, font_size=48, color=YELLOW)
# num.add_updater(lambda n: n.set_value(tracker.get_value()))

# --- Common gotchas (Manim CE) ---
# USE Create() NOT ShowCreation()
# USE axes.plot() NOT axes.get_graph()
# USE np.maximum(0, x) NOT max(0, x) in lambdas
# USE from manim import * NOT from manimlib import *
# Axes default: x_length = frame_width-2, y_length = frame_height-2
