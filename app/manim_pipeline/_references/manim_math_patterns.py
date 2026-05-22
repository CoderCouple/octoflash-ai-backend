"""
Comprehensive Manim CE Mathematical Animation Patterns
=======================================================
A reference library of 3Blue1Brown-style animation patterns for
Octoflash's Claude-powered script generation.

All code uses Manim Community Edition (`from manim import *`).
Patterns use: TransformMatchingTex, ValueTracker, always_redraw,
proper coloring to highlight changing terms, and smooth transitions.

Categories:
1. Equation Derivation Sequences
2. Matrix Animations
3. Calculus Animations
4. Probability & Statistics
5. Graph Theory
"""

from manim import *
import numpy as np


# =============================================================================
# COLOR PALETTE (3b1b-inspired, high-contrast on dark background)
# =============================================================================
BG_COLOR       = "#000000"
ACCENT_BLUE    = "#4fc3f7"
ACCENT_ORANGE  = "#ff9800"
ACCENT_GREEN   = "#66bb6a"
ACCENT_RED     = "#ef5350"
ACCENT_PURPLE  = "#ab47bc"
ACCENT_YELLOW  = "#ffee58"
ACCENT_CYAN    = "#26c6da"
ACCENT_PINK    = "#ec407a"
TEXT_PRIMARY    = "#ffffff"
TEXT_DIM        = "#9e9e9e"


# =============================================================================
# 1. EQUATION DERIVATION SEQUENCES
# =============================================================================

class QuadraticFormulaDerivation(Scene):
    """Step-by-step derivation of the quadratic formula using TransformMatchingTex.

    KEY PATTERN: Use double braces {{...}} to mark matchable substrings.
    TransformMatchingTex matches submobjects by their tex_string, so
    identical TeX between steps will smoothly morph in place while
    new/removed parts fade in/out.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Deriving the Quadratic Formula", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # -- Step 1: Standard form --
        step1 = MathTex(
            "{{a}}", "{{x}}^2", "+", "{{b}}", "{{x}}", "+", "{{c}}", "=", "0",
            font_size=44
        )
        step1.set_color_by_tex("a", ACCENT_BLUE)
        step1.set_color_by_tex("b", ACCENT_GREEN)
        step1.set_color_by_tex("c", ACCENT_ORANGE)
        step1.shift(UP * 0.5)

        label1 = Text("Start with standard form", font_size=20,
                       color=TEXT_DIM).to_edge(DOWN, buff=0.5)
        self.play(Write(step1), FadeIn(label1))
        self.wait(1.5)

        # -- Step 2: Divide by a --
        step2 = MathTex(
            "{{x}}^2", "+", "{{{b}} \\over {{a}}}", "{{x}}", "+",
            "{{{c}} \\over {{a}}}", "=", "0",
            font_size=44
        )
        step2.set_color_by_tex("a", ACCENT_BLUE)
        step2.set_color_by_tex("b", ACCENT_GREEN)
        step2.set_color_by_tex("c", ACCENT_ORANGE)
        step2.shift(UP * 0.5)

        label2 = Text("Divide everything by a", font_size=20,
                       color=TEXT_DIM).to_edge(DOWN, buff=0.5)
        self.play(
            TransformMatchingTex(step1, step2),
            FadeOut(label1), FadeIn(label2),
            run_time=2
        )
        self.wait(1.5)

        # -- Step 3: Complete the square --
        step3 = MathTex(
            "\\left(", "{{x}}", "+", "{{{b}} \\over 2{{a}}}", "\\right)^2",
            "=", "{{{b}}^2 - 4{{a}}{{c}} \\over 4{{a}}^2}",
            font_size=44
        )
        step3.set_color_by_tex("a", ACCENT_BLUE)
        step3.set_color_by_tex("b", ACCENT_GREEN)
        step3.set_color_by_tex("c", ACCENT_ORANGE)
        step3.shift(UP * 0.5)

        label3 = Text("Complete the square", font_size=20,
                       color=TEXT_DIM).to_edge(DOWN, buff=0.5)
        self.play(
            TransformMatchingTex(step2, step3),
            FadeOut(label2), FadeIn(label3),
            run_time=2
        )
        self.wait(1.5)

        # -- Step 4: Final formula --
        step4 = MathTex(
            "{{x}}", "=", "{-{{b}} \\pm \\sqrt{{{b}}^2 - 4{{a}}{{c}}} \\over 2{{a}}}",
            font_size=44
        )
        step4.set_color_by_tex("a", ACCENT_BLUE)
        step4.set_color_by_tex("b", ACCENT_GREEN)
        step4.set_color_by_tex("c", ACCENT_ORANGE)
        step4.shift(UP * 0.5)

        label4 = Text("The Quadratic Formula!", font_size=20,
                       color=ACCENT_YELLOW).to_edge(DOWN, buff=0.5)

        # Highlight box around the final result
        box = SurroundingRectangle(step4, color=ACCENT_YELLOW, buff=0.2,
                                    corner_radius=0.1)
        self.play(
            TransformMatchingTex(step3, step4),
            FadeOut(label3), FadeIn(label4),
            run_time=2
        )
        self.play(Create(box))
        self.wait(2)


class EulerIdentityDerivation(Scene):
    """Builds Euler's identity step-by-step with key_map for non-obvious matches."""

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Euler's Identity", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Step 1: Taylor series of e^x
        taylor = MathTex(
            "e^{{{x}}}", "=", "1", "+", "{{x}}", "+",
            "\\frac{{{x}}^2}{2!}", "+", "\\frac{{{x}}^3}{3!}", "+", "\\cdots",
            font_size=38
        )
        taylor.shift(UP * 1.0)
        self.play(Write(taylor), run_time=2)
        self.wait(1)

        # Step 2: Substitute x = i*theta
        substituted = MathTex(
            "e^{{{i\\theta}}}", "=", "1", "+", "{{i\\theta}}", "+",
            "\\frac{({{i\\theta}})^2}{2!}", "+",
            "\\frac{({{i\\theta}})^3}{3!}", "+", "\\cdots",
            font_size=38
        )
        substituted.shift(UP * 1.0)
        substituted.set_color_by_tex("i\\theta", ACCENT_CYAN)

        label = Text("Substitute x = i*theta", font_size=20,
                      color=TEXT_DIM).to_edge(DOWN, buff=0.5)
        self.play(
            TransformMatchingTex(taylor, substituted,
                                  key_map={"{{x}}": "{{i\\theta}}"}),
            FadeIn(label),
            run_time=2
        )
        self.wait(1.5)

        # Step 3: Separate real and imaginary parts
        separated = MathTex(
            "e^{i\\theta}", "=",
            "\\underbrace{\\left(1 - \\frac{\\theta^2}{2!} + \\cdots\\right)}_{\\cos\\theta}",
            "+",
            "i\\underbrace{\\left(\\theta - \\frac{\\theta^3}{3!} + \\cdots\\right)}_{\\sin\\theta}",
            font_size=34
        )
        separated.shift(UP * 0.5)
        separated[2].set_color(ACCENT_BLUE)
        separated[4].set_color(ACCENT_GREEN)

        label2 = Text("Group real and imaginary parts", font_size=20,
                       color=TEXT_DIM).to_edge(DOWN, buff=0.5)
        self.play(
            FadeOut(substituted),
            FadeIn(separated, shift=UP * 0.3),
            FadeOut(label), FadeIn(label2),
            run_time=2
        )
        self.wait(1.5)

        # Step 4: Euler's formula
        euler = MathTex(
            "e^{i\\theta}", "=", "\\cos\\theta", "+", "i\\sin\\theta",
            font_size=44
        )
        euler.shift(UP * 0.5)
        euler[2].set_color(ACCENT_BLUE)
        euler[4].set_color(ACCENT_GREEN)

        self.play(ReplacementTransform(separated, euler), run_time=2)
        self.wait(1)

        # Step 5: Set theta = pi
        identity = MathTex(
            "e^{i\\pi}", "+", "1", "=", "0",
            font_size=52
        )
        identity.shift(DOWN * 0.5)
        identity[0].set_color(ACCENT_PURPLE)

        box = SurroundingRectangle(identity, color=ACCENT_YELLOW, buff=0.25,
                                    corner_radius=0.1)

        label3 = Text("Set theta = pi: cos(pi) = -1, sin(pi) = 0",
                       font_size=20, color=ACCENT_YELLOW).to_edge(DOWN, buff=0.5)
        self.play(
            FadeOut(label2), FadeIn(label3),
            Write(identity), run_time=2
        )
        self.play(Create(box))
        self.wait(2)


class PythagoreanProof(Scene):
    """Visual + algebraic proof of the Pythagorean theorem.
    Combines geometric animation with equation transforms.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Pythagorean Theorem", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Draw the right triangle
        a_len, b_len = 2.0, 1.5
        triangle = Polygon(
            ORIGIN, RIGHT * a_len, RIGHT * a_len + UP * b_len,
            fill_opacity=0.2, fill_color=ACCENT_BLUE,
            stroke_color=ACCENT_BLUE, stroke_width=3
        ).shift(LEFT * 3 + DOWN * 0.5)

        # Labels on sides
        a_label = MathTex("a", font_size=32, color=ACCENT_GREEN).next_to(
            triangle, DOWN, buff=0.2)
        b_label = MathTex("b", font_size=32, color=ACCENT_ORANGE).next_to(
            triangle, RIGHT, buff=0.2)
        c_label = MathTex("c", font_size=32, color=ACCENT_RED).move_to(
            triangle.get_center() + UL * 0.5)

        # Right angle marker
        right_angle = Square(side_length=0.25, stroke_color=TEXT_DIM,
                              stroke_width=2, fill_opacity=0)
        right_angle.move_to(triangle.get_vertices()[1], aligned_edge=DL)

        self.play(Create(triangle), Write(a_label), Write(b_label),
                  Write(c_label), Create(right_angle), run_time=2)
        self.wait(1)

        # Equation steps on the right side
        eq1 = MathTex("{{a}}^2", "+", "{{b}}^2", "=", "{{c}}^2",
                       font_size=44)
        eq1.shift(RIGHT * 2.5 + UP * 0.5)
        eq1.set_color_by_tex("a", ACCENT_GREEN)
        eq1.set_color_by_tex("b", ACCENT_ORANGE)
        eq1.set_color_by_tex("c", ACCENT_RED)

        self.play(Write(eq1), run_time=1.5)
        self.wait(1)

        # Show squares on each side
        sq_a = Square(side_length=a_len, fill_opacity=0.15,
                       fill_color=ACCENT_GREEN, stroke_color=ACCENT_GREEN,
                       stroke_width=2)
        sq_a.next_to(triangle, DOWN, buff=0)
        sq_a_label = MathTex("a^2", font_size=28, color=ACCENT_GREEN).move_to(sq_a)

        sq_b = Square(side_length=b_len, fill_opacity=0.15,
                       fill_color=ACCENT_ORANGE, stroke_color=ACCENT_ORANGE,
                       stroke_width=2)
        sq_b.next_to(triangle, RIGHT, buff=0)
        sq_b_label = MathTex("b^2", font_size=28, color=ACCENT_ORANGE).move_to(sq_b)

        self.play(
            Create(sq_a), Write(sq_a_label),
            Create(sq_b), Write(sq_b_label),
            run_time=2
        )
        self.wait(1)

        # Highlight the relationship
        eq2 = MathTex(
            "{{c}}^2", "=", "{{a}}^2", "+", "{{b}}^2",
            font_size=44
        )
        eq2.shift(RIGHT * 2.5 + UP * 0.5)
        eq2.set_color_by_tex("a", ACCENT_GREEN)
        eq2.set_color_by_tex("b", ACCENT_ORANGE)
        eq2.set_color_by_tex("c", ACCENT_RED)

        self.play(TransformMatchingTex(eq1, eq2), run_time=1.5)

        box = SurroundingRectangle(eq2, color=ACCENT_YELLOW, buff=0.2)
        self.play(Create(box))
        self.wait(2)


# =============================================================================
# 2. MATRIX ANIMATIONS
# =============================================================================

class MatrixMultiplicationVisualization(Scene):
    """Animated matrix multiplication showing row-by-column dot products.

    KEY PATTERN: Use IntegerMatrix for display, highlight individual
    rows/columns with set_color, and animate the dot product calculation
    step by step.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Matrix Multiplication", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Define matrices
        mat_a = IntegerMatrix(
            [[1, 2], [3, 4]],
            left_bracket="[", right_bracket="]"
        ).set_color(ACCENT_BLUE).scale(0.8)

        times_sign = MathTex("\\times", font_size=40, color=TEXT_PRIMARY)

        mat_b = IntegerMatrix(
            [[5, 6], [7, 8]],
            left_bracket="[", right_bracket="]"
        ).set_color(ACCENT_GREEN).scale(0.8)

        equals_sign = MathTex("=", font_size=40, color=TEXT_PRIMARY)

        mat_c = IntegerMatrix(
            [[19, 22], [43, 50]],
            left_bracket="[", right_bracket="]"
        ).set_color(ACCENT_ORANGE).scale(0.8)

        # Arrange: A x B = C
        equation = VGroup(mat_a, times_sign, mat_b, equals_sign, mat_c)
        equation.arrange(RIGHT, buff=0.4).shift(UP * 0.5)

        # Show A and B first
        self.play(Write(mat_a), Write(times_sign), Write(mat_b), run_time=1.5)
        self.wait(0.5)

        # Highlight row 0 of A and col 0 of B
        row0_a = SurroundingRectangle(
            VGroup(mat_a.get_entries()[0], mat_a.get_entries()[1]),
            color=ACCENT_BLUE, buff=0.1
        )
        col0_b = SurroundingRectangle(
            VGroup(mat_b.get_entries()[0], mat_b.get_entries()[2]),
            color=ACCENT_GREEN, buff=0.1
        )
        self.play(Create(row0_a), Create(col0_b))

        # Show the dot product calculation
        dot_calc = MathTex(
            "1 \\cdot 5 + 2 \\cdot 7", "=", "19",
            font_size=32, color=ACCENT_YELLOW
        ).shift(DOWN * 1.5)
        self.play(Write(dot_calc), run_time=1.5)
        self.wait(1)

        # Show equals sign and result matrix
        self.play(
            FadeOut(row0_a), FadeOut(col0_b), FadeOut(dot_calc),
            Write(equals_sign), Write(mat_c),
            run_time=1.5
        )

        # Highlight each element of C one by one
        entries_c = mat_c.get_entries()
        calcs = [
            "1(5) + 2(7) = 19",
            "1(6) + 2(8) = 22",
            "3(5) + 4(7) = 43",
            "3(6) + 4(8) = 50",
        ]
        for i, (entry, calc_str) in enumerate(zip(entries_c, calcs)):
            highlight = SurroundingRectangle(entry, color=ACCENT_YELLOW, buff=0.1)
            calc_label = MathTex(calc_str, font_size=28,
                                  color=ACCENT_YELLOW).shift(DOWN * 2.0)
            self.play(Create(highlight), Write(calc_label), run_time=0.8)
            self.wait(0.5)
            self.play(FadeOut(highlight), FadeOut(calc_label), run_time=0.4)

        self.wait(1)


class EigenvalueVisualization(Scene):
    """Visualize how a 2x2 matrix transforms the plane, showing eigenvectors
    as the directions that only get scaled.

    KEY PATTERN: Use NumberPlane + Apply function to show linear transformation,
    then highlight eigenvectors that remain on their span.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Eigenvalues & Eigenvectors", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # The matrix: [[2, 1], [1, 2]]
        # Eigenvalues: 3 and 1
        # Eigenvectors: [1,1] (lambda=3) and [1,-1] (lambda=1)
        matrix_display = IntegerMatrix(
            [[2, 1], [1, 2]],
            left_bracket="[", right_bracket="]"
        ).scale(0.7).to_corner(UR, buff=0.8)
        matrix_display.set_color(ACCENT_BLUE)

        mat_label = MathTex("A =", font_size=32,
                             color=TEXT_PRIMARY).next_to(matrix_display, LEFT, buff=0.2)
        self.play(Write(mat_label), Write(matrix_display))

        # Number plane
        plane = NumberPlane(
            x_range=[-4, 4, 1], y_range=[-3, 3, 1],
            x_length=7, y_length=5,
            background_line_style={"stroke_color": TEXT_DIM, "stroke_opacity": 0.3}
        ).shift(DOWN * 0.3 + LEFT * 0.5)
        self.play(Create(plane), run_time=1.5)

        # Draw eigenvectors BEFORE transformation
        ev1_arrow = Arrow(
            plane.c2p(0, 0), plane.c2p(1, 1),
            color=ACCENT_GREEN, buff=0, stroke_width=4
        )
        ev2_arrow = Arrow(
            plane.c2p(0, 0), plane.c2p(1, -1),
            color=ACCENT_ORANGE, buff=0, stroke_width=4
        )
        ev1_label = MathTex(r"\vec{v}_1 = \begin{pmatrix}1\\1\end{pmatrix}",
                             font_size=24, color=ACCENT_GREEN)
        ev1_label.next_to(ev1_arrow, UR, buff=0.1)
        ev2_label = MathTex(r"\vec{v}_2 = \begin{pmatrix}1\\-1\end{pmatrix}",
                             font_size=24, color=ACCENT_ORANGE)
        ev2_label.next_to(ev2_arrow, DR, buff=0.1)

        self.play(Create(ev1_arrow), Write(ev1_label),
                  Create(ev2_arrow), Write(ev2_label), run_time=1.5)
        self.wait(1)

        # Apply the transformation
        transform_label = Text("Applying the transformation A...",
                                font_size=20, color=TEXT_DIM).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(transform_label))

        matrix = [[2, 1], [1, 2]]
        self.play(
            plane.animate.apply_matrix(matrix),
            ev1_arrow.animate.put_start_and_end_on(
                plane.c2p(0, 0), plane.c2p(3, 3)  # scaled by eigenvalue 3
            ),
            ev2_arrow.animate.put_start_and_end_on(
                plane.c2p(0, 0), plane.c2p(1, -1)  # scaled by eigenvalue 1
            ),
            run_time=3,
            rate_func=smooth
        )

        # Show eigenvalue equations
        eigen_eq1 = MathTex(
            "A", r"\vec{v}_1", "=", "3", r"\vec{v}_1",
            font_size=36
        ).shift(DOWN * 2.2 + LEFT * 2.5)
        eigen_eq1[1].set_color(ACCENT_GREEN)
        eigen_eq1[3].set_color(ACCENT_YELLOW)
        eigen_eq1[4].set_color(ACCENT_GREEN)

        eigen_eq2 = MathTex(
            "A", r"\vec{v}_2", "=", "1", r"\vec{v}_2",
            font_size=36
        ).shift(DOWN * 2.2 + RIGHT * 2.5)
        eigen_eq2[1].set_color(ACCENT_ORANGE)
        eigen_eq2[3].set_color(ACCENT_YELLOW)
        eigen_eq2[4].set_color(ACCENT_ORANGE)

        self.play(FadeOut(transform_label))
        self.play(Write(eigen_eq1), Write(eigen_eq2), run_time=1.5)
        self.wait(2)


class SVDVisualization(Scene):
    """Singular Value Decomposition: shows A = U * Sigma * V^T
    with the geometric interpretation of each step.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Singular Value Decomposition", font_size=38,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Show the SVD equation
        svd_eq = MathTex(
            "{{A}}", "=", "{{U}}", "{{\\Sigma}}", "{{V}}^T",
            font_size=44
        )
        svd_eq.set_color_by_tex("A", TEXT_PRIMARY)
        svd_eq.set_color_by_tex("U", ACCENT_BLUE)
        svd_eq.set_color_by_tex("\\Sigma", ACCENT_YELLOW)
        svd_eq.set_color_by_tex("V", ACCENT_GREEN)
        svd_eq.shift(UP * 1.8)
        self.play(Write(svd_eq), run_time=1.5)

        # Show what each matrix does
        descriptions = VGroup(
            MathTex("V^T", font_size=28, color=ACCENT_GREEN),
            Text(": Rotate", font_size=22, color=TEXT_DIM),
        ).arrange(RIGHT, buff=0.1)

        desc2 = VGroup(
            MathTex("\\Sigma", font_size=28, color=ACCENT_YELLOW),
            Text(": Scale", font_size=22, color=TEXT_DIM),
        ).arrange(RIGHT, buff=0.1)

        desc3 = VGroup(
            MathTex("U", font_size=28, color=ACCENT_BLUE),
            Text(": Rotate again", font_size=22, color=TEXT_DIM),
        ).arrange(RIGHT, buff=0.1)

        descs = VGroup(descriptions, desc2, desc3).arrange(RIGHT, buff=1.0)
        descs.shift(UP * 0.5)
        self.play(LaggedStartMap(FadeIn, descs, lag_ratio=0.3), run_time=2)
        self.wait(1)

        # Show geometric transformation steps on a unit circle
        plane = NumberPlane(
            x_range=[-3, 3, 1], y_range=[-2, 2, 1],
            x_length=5, y_length=3.5,
            background_line_style={"stroke_color": TEXT_DIM, "stroke_opacity": 0.2}
        ).shift(DOWN * 1.2)

        circle = Circle(radius=1, color=ACCENT_CYAN, stroke_width=3)
        circle.move_to(plane.c2p(0, 0))

        # Reference dot to track rotation
        dot = Dot(plane.c2p(1, 0), color=ACCENT_RED, radius=0.08)

        self.play(FadeOut(descs), Create(plane), Create(circle),
                  FadeIn(dot), run_time=1.5)

        # Step 1: V^T rotation
        step_label = Text("Step 1: V^T (rotate)", font_size=20,
                           color=ACCENT_GREEN).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(step_label))
        self.play(
            Rotate(circle, angle=PI / 6, about_point=plane.c2p(0, 0)),
            Rotate(dot, angle=PI / 6, about_point=plane.c2p(0, 0)),
            run_time=2
        )
        self.wait(0.5)

        # Step 2: Sigma (scale -- turns circle into ellipse)
        step_label2 = Text("Step 2: Sigma (scale axes)", font_size=20,
                            color=ACCENT_YELLOW).to_edge(DOWN, buff=0.4)
        self.play(FadeOut(step_label), FadeIn(step_label2))
        self.play(
            circle.animate.stretch(2.0, 0).stretch(0.5, 1),
            dot.animate.shift(RIGHT * 0.5),
            run_time=2
        )
        self.wait(0.5)

        # Step 3: U rotation
        step_label3 = Text("Step 3: U (rotate again)", font_size=20,
                            color=ACCENT_BLUE).to_edge(DOWN, buff=0.4)
        self.play(FadeOut(step_label2), FadeIn(step_label3))
        self.play(
            Rotate(circle, angle=-PI / 4, about_point=plane.c2p(0, 0)),
            Rotate(dot, angle=-PI / 4, about_point=plane.c2p(0, 0)),
            run_time=2
        )
        self.wait(2)


# =============================================================================
# 3. CALCULUS ANIMATIONS
# =============================================================================

class LimitDefinition(Scene):
    """Visualize the epsilon-delta definition of a limit using ValueTracker.

    KEY PATTERN: Use ValueTracker for epsilon, always_redraw for dynamic regions,
    and show how delta-neighborhood maps to epsilon-neighborhood.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Epsilon-Delta Definition of a Limit", font_size=36,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # The limit definition
        limit_def = MathTex(
            r"\forall\,\varepsilon > 0,\;\exists\,\delta > 0 :",
            r"|x - c| < \delta \implies |f(x) - L| < \varepsilon",
            font_size=30
        )
        limit_def[0].set_color(ACCENT_GREEN)
        limit_def[1].set_color(ACCENT_BLUE)
        limit_def.shift(UP * 1.8)
        self.play(Write(limit_def), run_time=2)

        # Axes for the function
        axes = Axes(
            x_range=[-1, 5, 1], y_range=[-1, 4, 1],
            x_length=7, y_length=3.5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2}
        ).shift(DOWN * 0.5)
        axis_labels = axes.get_axis_labels(
            x_label=MathTex("x", font_size=24),
            y_label=MathTex("f(x)", font_size=24)
        )
        self.play(Create(axes), Write(axis_labels), run_time=1)

        # Plot f(x) = sqrt(x)
        func = axes.plot(lambda x: np.sqrt(np.maximum(0, x)),
                          x_range=[0.01, 4.5], color=ACCENT_CYAN, stroke_width=3)
        self.play(Create(func), run_time=1.5)

        # Point of interest: c = 2, L = sqrt(2)
        c_val = 2.0
        L_val = np.sqrt(c_val)

        # Mark the point
        c_dot = Dot(axes.c2p(c_val, L_val), color=ACCENT_RED, radius=0.08)
        c_line = DashedLine(
            axes.c2p(c_val, 0), axes.c2p(c_val, L_val),
            color=TEXT_DIM, stroke_width=1
        )
        L_line = DashedLine(
            axes.c2p(0, L_val), axes.c2p(c_val, L_val),
            color=TEXT_DIM, stroke_width=1
        )

        c_label = MathTex("c", font_size=24, color=ACCENT_RED).next_to(
            axes.c2p(c_val, 0), DOWN, buff=0.15)
        L_label = MathTex("L", font_size=24, color=ACCENT_RED).next_to(
            axes.c2p(0, L_val), LEFT, buff=0.15)

        self.play(
            FadeIn(c_dot), Create(c_line), Create(L_line),
            Write(c_label), Write(L_label),
            run_time=1
        )

        # ValueTracker for epsilon
        epsilon = ValueTracker(1.0)

        # Dynamic epsilon band (horizontal)
        epsilon_band = always_redraw(lambda: Rectangle(
            width=axes.x_length,
            height=axes.y_length * (2 * epsilon.get_value()) / 5,
            fill_color=ACCENT_GREEN, fill_opacity=0.15,
            stroke_color=ACCENT_GREEN, stroke_width=1,
        ).move_to(axes.c2p(2.25, L_val)))

        # Dynamic delta band (vertical)
        delta_band = always_redraw(lambda: Rectangle(
            width=axes.x_length * (2 * epsilon.get_value() * 0.7) / 6,
            height=axes.y_length,
            fill_color=ACCENT_BLUE, fill_opacity=0.15,
            stroke_color=ACCENT_BLUE, stroke_width=1,
        ).move_to(axes.c2p(c_val, 1.5)))

        # Labels
        eps_label = always_redraw(lambda: MathTex(
            f"\\varepsilon = {epsilon.get_value():.2f}",
            font_size=24, color=ACCENT_GREEN
        ).to_edge(DOWN, buff=0.4))

        self.play(FadeIn(epsilon_band), FadeIn(delta_band), FadeIn(eps_label))

        # Shrink epsilon -- the 3b1b way of building intuition
        self.play(epsilon.animate.set_value(0.5), run_time=2, rate_func=smooth)
        self.wait(0.5)
        self.play(epsilon.animate.set_value(0.2), run_time=2, rate_func=smooth)
        self.wait(0.5)
        self.play(epsilon.animate.set_value(0.05), run_time=3, rate_func=smooth)
        self.wait(1)

        conclusion = Text("As epsilon shrinks, delta must shrink too!",
                           font_size=22, color=ACCENT_YELLOW).shift(DOWN * 2.8)
        self.play(FadeIn(conclusion))
        self.wait(2)


class DerivativeTangentLine(Scene):
    """Animate the derivative as the slope of a tangent line.
    ValueTracker controls the point x; always_redraw draws the tangent.

    THE CORE 3B1B PATTERN:
    1. Plot a function
    2. Use ValueTracker for the x-position
    3. always_redraw the tangent line and slope label
    4. Animate the tracker to sweep along the curve
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("The Derivative as a Tangent Line", font_size=38,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # The function: f(x) = x^2 / 4
        func = lambda x: x**2 / 4
        deriv = lambda x: x / 2  # f'(x) = x/2

        axes = Axes(
            x_range=[-4, 4, 1], y_range=[-0.5, 4.5, 1],
            x_length=7, y_length=3.5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2}
        ).shift(DOWN * 0.3)
        axis_labels = axes.get_axis_labels(
            x_label=MathTex("x", font_size=24),
            y_label=MathTex("f(x)", font_size=24)
        )

        curve = axes.plot(func, x_range=[-4, 4], color=ACCENT_CYAN,
                           stroke_width=3)

        eq = MathTex(r"f(x) = \frac{x^2}{4}", font_size=32,
                      color=ACCENT_CYAN).shift(UP * 1.6 + RIGHT * 3)

        self.play(Create(axes), Write(axis_labels), Create(curve),
                  Write(eq), run_time=2)

        # ValueTracker for x position
        x_val = ValueTracker(-3)

        # Dynamic dot on the curve
        dot = always_redraw(lambda: Dot(
            axes.c2p(x_val.get_value(), func(x_val.get_value())),
            color=ACCENT_RED, radius=0.1
        ))

        # Dynamic tangent line
        tangent = always_redraw(lambda: axes.plot(
            lambda x: deriv(x_val.get_value()) * (x - x_val.get_value()) + func(x_val.get_value()),
            x_range=[x_val.get_value() - 2, x_val.get_value() + 2],
            color=ACCENT_YELLOW, stroke_width=2
        ))

        # Dynamic slope label
        slope_label = always_redraw(lambda: MathTex(
            f"f'({x_val.get_value():.1f}) = {deriv(x_val.get_value()):.2f}",
            font_size=24, color=ACCENT_YELLOW
        ).next_to(dot, UR, buff=0.2))

        self.play(FadeIn(dot), Create(tangent), FadeIn(slope_label))

        # Sweep the point along the curve
        self.play(x_val.animate.set_value(3), run_time=6, rate_func=linear)
        self.wait(1)

        # Show the derivative function
        deriv_curve = axes.plot(deriv, x_range=[-4, 4], color=ACCENT_ORANGE,
                                 stroke_width=3)
        deriv_label = MathTex(r"f'(x) = \frac{x}{2}", font_size=32,
                               color=ACCENT_ORANGE).shift(UP * 1.6 + LEFT * 3)
        self.play(Create(deriv_curve), Write(deriv_label), run_time=2)
        self.wait(2)


class IntegralAreaUnderCurve(Scene):
    """Riemann sum animation that approaches the definite integral.

    KEY PATTERN: Use ValueTracker for the number of rectangles,
    always_redraw to rebuild the Riemann sum bars, showing convergence.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("The Definite Integral", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        func = lambda x: 0.2 * (x - 1) * (x - 3) * (x - 5) + 3

        axes = Axes(
            x_range=[0, 6, 1], y_range=[0, 5, 1],
            x_length=7, y_length=3.5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2}
        ).shift(DOWN * 0.4)
        axis_labels = axes.get_axis_labels(
            x_label=MathTex("x", font_size=24),
            y_label=MathTex("f(x)", font_size=24)
        )

        curve = axes.plot(func, x_range=[0.5, 5.5], color=ACCENT_CYAN,
                           stroke_width=3)

        self.play(Create(axes), Write(axis_labels), Create(curve), run_time=2)

        # Show the integral formula
        integral_eq = MathTex(
            r"\int_a^b f(x)\,dx", r"= \lim_{n\to\infty} \sum_{i=1}^{n} f(x_i)\,\Delta x",
            font_size=32
        ).shift(UP * 1.7)
        integral_eq[0].set_color(ACCENT_GREEN)
        integral_eq[1].set_color(ACCENT_ORANGE)
        self.play(Write(integral_eq), run_time=1.5)

        # ValueTracker for number of rectangles
        n_rects = ValueTracker(4)

        # Dynamic Riemann sum rectangles
        riemann = always_redraw(lambda: axes.get_riemann_rectangles(
            curve,
            x_range=[1, 5],
            dx=4 / max(1, int(n_rects.get_value())),
            color=[ACCENT_BLUE, ACCENT_GREEN],
            fill_opacity=0.5,
            stroke_width=1,
            stroke_color=TEXT_PRIMARY,
        ))

        n_label = always_redraw(lambda: MathTex(
            f"n = {int(n_rects.get_value())}",
            font_size=28, color=ACCENT_YELLOW
        ).to_edge(DOWN, buff=0.5))

        self.play(FadeIn(riemann), FadeIn(n_label))
        self.wait(1)

        # Increase number of rectangles progressively
        for target_n in [8, 16, 32, 64]:
            self.play(
                n_rects.animate.set_value(target_n),
                run_time=2, rate_func=smooth
            )
            self.wait(0.5)

        conclusion = Text("As n approaches infinity, the sum becomes the integral",
                           font_size=20, color=ACCENT_YELLOW).to_edge(DOWN, buff=0.3)
        self.play(FadeOut(n_label), FadeIn(conclusion))
        self.wait(2)


class TaylorSeriesApproximation(Scene):
    """Animate Taylor polynomial approximations converging to sin(x).

    KEY PATTERN: Use ValueTracker for the polynomial degree,
    always_redraw the Taylor polynomial, and show convergence.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Taylor Series for sin(x)", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        axes = Axes(
            x_range=[-7, 7, 1], y_range=[-2, 2, 1],
            x_length=10, y_length=3.5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2}
        ).shift(DOWN * 0.4)
        axis_labels = axes.get_axis_labels(
            x_label=MathTex("x", font_size=24),
            y_label=MathTex("y", font_size=24)
        )

        # Plot sin(x)
        sin_curve = axes.plot(np.sin, x_range=[-7, 7], color=ACCENT_CYAN,
                               stroke_width=3)
        sin_label = MathTex(r"\sin(x)", font_size=28,
                             color=ACCENT_CYAN).shift(UP * 1.6 + RIGHT * 4)

        self.play(Create(axes), Write(axis_labels), Create(sin_curve),
                  Write(sin_label), run_time=2)

        # Taylor series terms: sin(x) = x - x^3/3! + x^5/5! - x^7/7! + ...
        def taylor_sin(x, n_terms):
            """Compute Taylor approximation of sin(x) with n_terms terms."""
            result = np.zeros_like(x, dtype=float)
            for k in range(n_terms):
                sign = (-1) ** k
                power = 2 * k + 1
                factorial = 1
                for j in range(1, power + 1):
                    factorial *= j
                result += sign * x**power / factorial
            return result

        # Formula display
        formulas = [
            MathTex(r"P_1(x) = x", font_size=28, color=ACCENT_ORANGE),
            MathTex(r"P_3(x) = x - \frac{x^3}{3!}", font_size=28, color=ACCENT_ORANGE),
            MathTex(r"P_5(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!}",
                     font_size=28, color=ACCENT_ORANGE),
            MathTex(r"P_7(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!} - \frac{x^7}{7!}",
                     font_size=26, color=ACCENT_ORANGE),
            MathTex(r"P_9(x) = x - \frac{x^3}{3!} + \cdots + \frac{x^9}{9!}",
                     font_size=26, color=ACCENT_ORANGE),
        ]

        colors = [ACCENT_RED, ACCENT_ORANGE, ACCENT_YELLOW, ACCENT_GREEN, ACCENT_PURPLE]
        prev_approx = None
        prev_formula = None

        for i, (n_terms, formula, color) in enumerate(
            zip([1, 2, 3, 4, 5], formulas, colors)
        ):
            approx = axes.plot(
                lambda x, n=n_terms: taylor_sin(x, n),
                x_range=[-6.5, 6.5],
                color=color, stroke_width=2.5
            )

            formula.shift(UP * 1.6 + LEFT * 2)

            anims = [Create(approx)]
            if prev_formula:
                anims.append(ReplacementTransform(prev_formula, formula))
            else:
                anims.append(Write(formula))

            if prev_approx:
                anims.append(prev_approx.animate.set_stroke(opacity=0.2))

            self.play(*anims, run_time=1.5)
            self.wait(0.5)

            prev_approx = approx
            prev_formula = formula

        conclusion = Text("More terms = better approximation!",
                           font_size=22, color=ACCENT_YELLOW).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(conclusion))
        self.wait(2)


# =============================================================================
# 4. PROBABILITY & STATISTICS
# =============================================================================

class NormalDistributionExplorer(Scene):
    """Explore the normal distribution with interactive mu and sigma.

    KEY PATTERN: Two ValueTrackers (mu, sigma), always_redraw the
    bell curve and shaded area, animate parameter changes.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Normal Distribution", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Formula
        formula = MathTex(
            r"f(x) = \frac{1}{\sigma\sqrt{2\pi}}",
            r"e^{-\frac{(x-\mu)^2}{2\sigma^2}}",
            font_size=32
        ).shift(UP * 1.7)
        formula[0].set_color(ACCENT_BLUE)
        formula[1].set_color(ACCENT_GREEN)
        self.play(Write(formula), run_time=1.5)

        axes = Axes(
            x_range=[-5, 5, 1], y_range=[0, 0.8, 0.2],
            x_length=8, y_length=3.0,
            axis_config={"color": TEXT_DIM, "stroke_width": 2}
        ).shift(DOWN * 0.5)
        axis_labels = axes.get_axis_labels(
            x_label=MathTex("x", font_size=24),
            y_label=MathTex("f(x)", font_size=24)
        )
        self.play(Create(axes), Write(axis_labels), run_time=1)

        # ValueTrackers for mu and sigma
        mu = ValueTracker(0)
        sigma = ValueTracker(1)

        # Dynamic normal distribution curve
        def normal_pdf(x, mu_val, sigma_val):
            return (1 / (sigma_val * np.sqrt(2 * np.pi))) * \
                   np.exp(-((x - mu_val)**2) / (2 * sigma_val**2))

        bell_curve = always_redraw(lambda: axes.plot(
            lambda x: normal_pdf(x, mu.get_value(), sigma.get_value()),
            x_range=[-4.5, 4.5],
            color=ACCENT_CYAN, stroke_width=3
        ))

        # Shaded area under curve (within 1 sigma)
        shaded_area = always_redraw(lambda: axes.get_area(
            axes.plot(
                lambda x: normal_pdf(x, mu.get_value(), sigma.get_value()),
                x_range=[
                    mu.get_value() - sigma.get_value(),
                    mu.get_value() + sigma.get_value()
                ]
            ),
            x_range=[
                mu.get_value() - sigma.get_value(),
                mu.get_value() + sigma.get_value()
            ],
            color=ACCENT_BLUE, opacity=0.3
        ))

        # Dynamic labels
        param_label = always_redraw(lambda: VGroup(
            MathTex(f"\\mu = {mu.get_value():.1f}",
                     font_size=28, color=ACCENT_ORANGE),
            MathTex(f"\\sigma = {sigma.get_value():.1f}",
                     font_size=28, color=ACCENT_GREEN),
        ).arrange(RIGHT, buff=1.0).to_edge(DOWN, buff=0.4))

        self.play(Create(bell_curve), FadeIn(shaded_area), FadeIn(param_label))
        self.wait(1)

        # Animate mu change (shift the distribution)
        caption = Text("Shifting the mean (mu)", font_size=20,
                        color=TEXT_DIM).to_edge(DOWN, buff=0.8)
        self.play(FadeIn(caption))
        self.play(mu.animate.set_value(2), run_time=2, rate_func=smooth)
        self.play(mu.animate.set_value(-1), run_time=2, rate_func=smooth)
        self.play(mu.animate.set_value(0), run_time=1.5, rate_func=smooth)
        self.play(FadeOut(caption))
        self.wait(0.5)

        # Animate sigma change (widen/narrow)
        caption2 = Text("Changing the spread (sigma)", font_size=20,
                          color=TEXT_DIM).to_edge(DOWN, buff=0.8)
        self.play(FadeIn(caption2))
        self.play(sigma.animate.set_value(2), run_time=2, rate_func=smooth)
        self.play(sigma.animate.set_value(0.5), run_time=2, rate_func=smooth)
        self.play(sigma.animate.set_value(1), run_time=1.5, rate_func=smooth)
        self.play(FadeOut(caption2))
        self.wait(1)

        # 68-95-99.7 rule
        rule_text = MathTex(
            r"P(\mu - \sigma < X < \mu + \sigma) \approx 68.27\%",
            font_size=28, color=ACCENT_YELLOW
        ).to_edge(DOWN, buff=0.4)
        self.play(Write(rule_text))
        self.wait(2)


class BayesTheoremVisualization(Scene):
    """Visualize Bayes' theorem with a concrete medical test example.
    Uses area-proportional rectangles and TransformMatchingTex.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Bayes' Theorem", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Show the formula with TransformMatchingTex steps
        bayes_v1 = MathTex(
            "P({{A}} | {{B}})", "=",
            "\\frac{P({{B}} | {{A}}) \\cdot P({{A}})}{P({{B}})}",
            font_size=38
        )
        bayes_v1.set_color_by_tex("A", ACCENT_BLUE)
        bayes_v1.set_color_by_tex("B", ACCENT_GREEN)
        bayes_v1.shift(UP * 1.7)
        self.play(Write(bayes_v1), run_time=2)
        self.wait(1)

        # Concrete example: medical test
        # Disease prevalence: 1%
        # Test sensitivity: 90% (true positive rate)
        # Test specificity: 95% (true negative rate)

        example_label = Text("Medical Test Example", font_size=24,
                              color=ACCENT_YELLOW).shift(UP * 0.6)
        self.play(FadeIn(example_label))

        # Population rectangle
        pop_rect = Rectangle(width=8, height=2.5, stroke_color=TEXT_DIM,
                              stroke_width=2).shift(DOWN * 1.0)

        # Sick (1%) vs Healthy (99%)
        sick_width = 8 * 0.01
        healthy_width = 8 * 0.99

        sick_rect = Rectangle(
            width=sick_width, height=2.5,
            fill_color=ACCENT_RED, fill_opacity=0.4,
            stroke_color=ACCENT_RED, stroke_width=1
        ).align_to(pop_rect, LEFT).align_to(pop_rect, DOWN)

        healthy_rect = Rectangle(
            width=healthy_width, height=2.5,
            fill_color=ACCENT_GREEN, fill_opacity=0.15,
            stroke_color=ACCENT_GREEN, stroke_width=1
        ).align_to(pop_rect, RIGHT).align_to(pop_rect, DOWN)

        sick_label = Text("Sick: 1%", font_size=16,
                           color=ACCENT_RED).next_to(sick_rect, UP, buff=0.1)
        healthy_label = Text("Healthy: 99%", font_size=16,
                              color=ACCENT_GREEN).next_to(healthy_rect, UP, buff=0.1)

        self.play(
            Create(pop_rect), FadeIn(sick_rect), FadeIn(healthy_rect),
            Write(sick_label), Write(healthy_label),
            run_time=2
        )
        self.wait(1)

        # Highlight true positives and false positives
        # True positive: 90% of sick = 0.9%
        # False positive: 5% of healthy = 4.95%
        tp_rect = Rectangle(
            width=sick_width, height=2.5 * 0.9,
            fill_color=ACCENT_YELLOW, fill_opacity=0.6,
            stroke_color=ACCENT_YELLOW, stroke_width=2
        ).align_to(sick_rect, LEFT).align_to(sick_rect, DOWN)

        fp_rect = Rectangle(
            width=healthy_width * 0.05, height=2.5,
            fill_color=ACCENT_ORANGE, fill_opacity=0.4,
            stroke_color=ACCENT_ORANGE, stroke_width=2
        ).align_to(healthy_rect, LEFT).align_to(healthy_rect, DOWN)

        tp_label = Text("TP: 0.9%", font_size=14,
                         color=ACCENT_YELLOW).next_to(tp_rect, DOWN, buff=0.1)
        fp_label = Text("FP: 4.95%", font_size=14,
                         color=ACCENT_ORANGE).next_to(fp_rect, DOWN, buff=0.1)

        self.play(FadeIn(tp_rect), FadeIn(fp_rect),
                  Write(tp_label), Write(fp_label), run_time=1.5)
        self.wait(1)

        # Calculate the result
        result = MathTex(
            r"P(\text{Sick}|\text{Positive}) = \frac{0.009}{0.009 + 0.0495}",
            r"\approx 15.4\%",
            font_size=30
        ).to_edge(DOWN, buff=0.3)
        result[0].set_color(ACCENT_BLUE)
        result[1].set_color(ACCENT_YELLOW)

        self.play(Write(result), run_time=2)

        insight = Text("Even with a positive test, only ~15% chance of being sick!",
                        font_size=20, color=ACCENT_PINK).next_to(result, UP, buff=0.2)
        self.play(FadeIn(insight))
        self.wait(2)


class HistogramAnimation(Scene):
    """Animate a histogram being built bar-by-bar, then transform
    into a smooth distribution using BarChart + ValueTracker.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("From Histogram to Distribution", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Build initial BarChart
        values = [2, 5, 8, 12, 15, 12, 8, 5, 2]
        bar_names = [str(i) for i in range(1, 10)]

        chart = BarChart(
            values,
            bar_names=bar_names,
            y_range=[0, 18, 3],
            x_length=8,
            y_length=3.5,
            bar_width=0.7,
            bar_colors=[ACCENT_BLUE, ACCENT_CYAN, ACCENT_GREEN,
                         ACCENT_YELLOW, ACCENT_ORANGE],
        ).shift(DOWN * 0.3)

        self.play(Create(chart), run_time=2)
        self.wait(1)

        # Animate bars growing one by one
        # (BarChart's change_bar_values method)
        new_values_1 = [3, 7, 11, 16, 20, 16, 11, 7, 3]
        self.play(chart.animate.change_bar_values(new_values_1), run_time=2)
        self.wait(0.5)

        # Add more data, bars get taller and smoother
        new_values_2 = [4, 8, 14, 22, 28, 22, 14, 8, 4]
        self.play(chart.animate.change_bar_values(new_values_2), run_time=2)
        self.wait(1)

        # Overlay a smooth normal curve
        axes = Axes(
            x_range=[0, 10, 1], y_range=[0, 30, 5],
            x_length=8, y_length=3.5,
            axis_config={"color": BLUE, "stroke_opacity": 0}
        ).shift(DOWN * 0.3)

        smooth_curve = axes.plot(
            lambda x: 28 * np.exp(-((x - 5)**2) / (2 * 1.5**2)),
            x_range=[0.5, 9.5],
            color=ACCENT_RED, stroke_width=3
        )

        label = Text("As sample size grows, histogram approaches the distribution",
                       font_size=20, color=ACCENT_YELLOW).to_edge(DOWN, buff=0.4)

        self.play(Create(smooth_curve), FadeIn(label), run_time=2)
        self.wait(2)


# =============================================================================
# 5. GRAPH THEORY
# =============================================================================

class GraphTheoryBasics(Scene):
    """Animate graph creation with node-by-node and edge-by-edge animations.

    KEY PATTERN: Use Manim's Graph mobject with labels, then animate
    layout changes and pathfinding.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Graph Theory Fundamentals", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Create a graph step by step
        vertices = [1, 2, 3, 4, 5, 6]
        edges = [(1, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5), (4, 6), (5, 6)]

        # Start with just vertices
        g = Graph(
            vertices, [],
            labels=True,
            layout="circular",
            layout_scale=2.0,
            vertex_config={
                "fill_color": ACCENT_BLUE,
                "stroke_color": ACCENT_CYAN,
                "stroke_width": 2,
                "radius": 0.3,
            },
            label_fill_color=TEXT_PRIMARY,
        ).shift(DOWN * 0.3)

        self.play(Create(g), run_time=2)
        self.wait(0.5)

        # Add edges one by one
        for edge in edges:
            self.play(
                g.animate.add_edges(
                    edge,
                    edge_config={edge: {"stroke_color": TEXT_DIM, "stroke_width": 2}}
                ),
                run_time=0.5
            )
        self.wait(1)

        # Highlight a path (BFS/DFS style)
        path = [1, 2, 4, 6]
        path_label = Text("Shortest path: 1 -> 2 -> 4 -> 6",
                           font_size=22, color=ACCENT_YELLOW).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(path_label))

        for i in range(len(path)):
            node = path[i]
            self.play(
                g.vertices[node].animate.set_fill(ACCENT_GREEN, opacity=0.8),
                run_time=0.5
            )
            if i > 0:
                prev_node = path[i - 1]
                edge_key = (min(prev_node, node), max(prev_node, node))
                if edge_key in g.edges:
                    self.play(
                        g.edges[edge_key].animate.set_stroke(ACCENT_GREEN, width=4),
                        run_time=0.4
                    )

        self.wait(1)

        # Change layout
        layout_label = Text("Switching to spring layout...",
                             font_size=20, color=TEXT_DIM).to_edge(DOWN, buff=0.7)
        self.play(FadeOut(path_label), FadeIn(layout_label))
        self.play(
            g.animate.change_layout("spring", layout_scale=2.0),
            run_time=2
        )
        self.wait(1)

        self.play(
            g.animate.change_layout("kamada_kawai", layout_scale=2.0),
            run_time=2
        )
        self.wait(2)


class DijkstraVisualization(Scene):
    """Animate Dijkstra's shortest path algorithm step by step.
    Shows visited nodes in green, frontier in yellow, unvisited in blue.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Dijkstra's Algorithm", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Weighted graph using manual layout
        vertices = [0, 1, 2, 3, 4]
        edges = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 4), (3, 4)]
        weights = {(0, 1): 4, (0, 2): 2, (1, 2): 1, (1, 3): 5, (2, 4): 3, (3, 4): 1}

        positions = {
            0: LEFT * 3 + UP * 0.5,
            1: LEFT * 1 + UP * 1.5,
            2: LEFT * 1 + DOWN * 1.0,
            3: RIGHT * 1.5 + UP * 1.5,
            4: RIGHT * 3 + DOWN * 0.0,
        }

        # Create nodes manually
        nodes = {}
        node_labels = {}
        for v in vertices:
            node = Circle(radius=0.3, fill_color=ACCENT_BLUE, fill_opacity=0.7,
                           stroke_color=ACCENT_CYAN, stroke_width=2)
            node.move_to(positions[v])
            label = Text(str(v), font_size=22, color=TEXT_PRIMARY).move_to(node)
            nodes[v] = node
            node_labels[v] = label

        # Create edges manually with weight labels
        edge_lines = {}
        weight_labels = {}
        for (u, v) in edges:
            line = Line(
                positions[u], positions[v],
                color=TEXT_DIM, stroke_width=2
            )
            mid = (positions[u] + positions[v]) / 2
            w_label = Text(str(weights[(u, v)]), font_size=18, color=ACCENT_ORANGE)
            w_label.move_to(mid + UP * 0.2 + RIGHT * 0.1)
            edge_lines[(u, v)] = line
            weight_labels[(u, v)] = w_label

        # Draw everything
        for line in edge_lines.values():
            self.play(Create(line), run_time=0.3)
        for v in vertices:
            self.play(FadeIn(nodes[v]), FadeIn(node_labels[v]), run_time=0.3)
        for w_label in weight_labels.values():
            self.play(FadeIn(w_label), run_time=0.2)

        self.wait(1)

        # Distance labels
        dist_labels = {}
        for v in vertices:
            d_text = MathTex(r"\infty", font_size=22, color=ACCENT_RED)
            d_text.next_to(nodes[v], DOWN, buff=0.15)
            dist_labels[v] = d_text
            self.play(FadeIn(d_text), run_time=0.2)

        # Start Dijkstra from node 0
        # Update distance of start node
        new_d0 = MathTex("0", font_size=22, color=ACCENT_GREEN)
        new_d0.next_to(nodes[0], DOWN, buff=0.15)
        self.play(
            ReplacementTransform(dist_labels[0], new_d0),
            nodes[0].animate.set_fill(ACCENT_GREEN, opacity=0.8),
            run_time=0.8
        )
        dist_labels[0] = new_d0

        # Simulate algorithm steps
        steps = [
            # (visited_node, updates: [(neighbor, new_dist)])
            (0, [(1, 4), (2, 2)]),
            (2, [(1, 3), (4, 5)]),
            (1, [(3, 8)]),
            (4, []),
            (3, []),
        ]

        for visited, updates in steps:
            # Mark as visited
            self.play(
                nodes[visited].animate.set_fill(ACCENT_GREEN, opacity=0.8),
                run_time=0.5
            )

            for neighbor, new_dist in updates:
                # Highlight the edge being relaxed
                edge_key = (min(visited, neighbor), max(visited, neighbor))
                if edge_key in edge_lines:
                    self.play(
                        edge_lines[edge_key].animate.set_stroke(ACCENT_YELLOW, width=4),
                        run_time=0.3
                    )

                # Update distance label
                new_label = MathTex(str(new_dist), font_size=22, color=ACCENT_YELLOW)
                new_label.next_to(nodes[neighbor], DOWN, buff=0.15)
                self.play(
                    ReplacementTransform(dist_labels[neighbor], new_label),
                    run_time=0.5
                )
                dist_labels[neighbor] = new_label

            self.wait(0.3)

        # Highlight final shortest path: 0 -> 2 -> 4
        path_edges = [(0, 2), (2, 4)]
        for edge_key in path_edges:
            if edge_key in edge_lines:
                self.play(
                    edge_lines[edge_key].animate.set_stroke(ACCENT_GREEN, width=5),
                    run_time=0.5
                )

        result = Text("Shortest path 0->4: cost = 5 (via 0->2->4)",
                        font_size=22, color=ACCENT_GREEN).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(result))
        self.wait(2)


class BinaryTreeTraversal(Scene):
    """Animate a binary tree with in-order, pre-order, and level-order traversals.
    Shows nodes lighting up in traversal order.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Binary Tree Traversals", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # Build a binary tree manually
        # Tree structure:
        #        1
        #       / \
        #      2   3
        #     / \ / \
        #    4  5 6  7

        positions = {
            1: UP * 1.2,
            2: LEFT * 2.5 + DOWN * 0.3,
            3: RIGHT * 2.5 + DOWN * 0.3,
            4: LEFT * 3.5 + DOWN * 1.8,
            5: LEFT * 1.5 + DOWN * 1.8,
            6: RIGHT * 1.5 + DOWN * 1.8,
            7: RIGHT * 3.5 + DOWN * 1.8,
        }

        tree_edges = [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)]

        # Create nodes
        nodes = {}
        node_texts = {}
        for v, pos in positions.items():
            node = Circle(radius=0.35, fill_color=ACCENT_BLUE, fill_opacity=0.5,
                           stroke_color=ACCENT_CYAN, stroke_width=2)
            node.move_to(pos)
            text = Text(str(v), font_size=24, color=TEXT_PRIMARY).move_to(pos)
            nodes[v] = node
            node_texts[v] = text

        # Create edges
        lines = {}
        for parent, child in tree_edges:
            line = Line(positions[parent], positions[child],
                         color=TEXT_DIM, stroke_width=2)
            lines[(parent, child)] = line

        # Draw tree
        for line in lines.values():
            self.add(line)
        for v in sorted(nodes.keys()):
            self.add(nodes[v], node_texts[v])
        self.play(*[FadeIn(mob) for mob in self.mobjects[1:]], run_time=1.5)
        self.wait(1)

        # In-order traversal: 4, 2, 5, 1, 6, 3, 7
        inorder = [4, 2, 5, 1, 6, 3, 7]
        traversal_label = Text("In-order: Left -> Root -> Right",
                                font_size=22, color=ACCENT_YELLOW).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(traversal_label))

        order_display = VGroup()
        for i, v in enumerate(inorder):
            self.play(
                nodes[v].animate.set_fill(ACCENT_GREEN, opacity=0.8),
                run_time=0.4
            )
            num = Text(str(v), font_size=20, color=ACCENT_GREEN)
            if i == 0:
                num.shift(DOWN * 2.7 + LEFT * 3)
            else:
                num.next_to(order_display[-1], RIGHT, buff=0.3)
            order_display.add(num)
            self.play(FadeIn(num), run_time=0.2)

        self.wait(1)

        # Reset colors
        self.play(
            *[nodes[v].animate.set_fill(ACCENT_BLUE, opacity=0.5) for v in nodes],
            FadeOut(order_display), FadeOut(traversal_label),
            run_time=0.8
        )

        # Pre-order traversal: 1, 2, 4, 5, 3, 6, 7
        preorder = [1, 2, 4, 5, 3, 6, 7]
        traversal_label2 = Text("Pre-order: Root -> Left -> Right",
                                 font_size=22, color=ACCENT_ORANGE).to_edge(DOWN, buff=0.4)
        self.play(FadeIn(traversal_label2))

        order_display2 = VGroup()
        for i, v in enumerate(preorder):
            self.play(
                nodes[v].animate.set_fill(ACCENT_ORANGE, opacity=0.8),
                run_time=0.4
            )
            num = Text(str(v), font_size=20, color=ACCENT_ORANGE)
            if i == 0:
                num.shift(DOWN * 2.7 + LEFT * 3)
            else:
                num.next_to(order_display2[-1], RIGHT, buff=0.3)
            order_display2.add(num)
            self.play(FadeIn(num), run_time=0.2)

        self.wait(2)


# =============================================================================
# UTILITY PATTERNS (reusable building blocks)
# =============================================================================

class EquationHighlightPattern(Scene):
    """Demonstrates the pattern for highlighting specific terms in equations,
    stepping through with color changes and SurroundingRectangle.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        # Pattern: Use set_color_by_tex and SurroundingRectangle
        # to draw attention to specific terms during a derivation.

        eq = MathTex(
            "E", "=", "m", "c", "^2",
            font_size=52
        )
        self.play(Write(eq))
        self.wait(1)

        # Highlight 'm' (mass)
        mass_box = SurroundingRectangle(eq[2], color=ACCENT_BLUE, buff=0.1)
        mass_label = Text("mass", font_size=24, color=ACCENT_BLUE).next_to(mass_box, DOWN)
        self.play(Create(mass_box), Write(mass_label))
        self.wait(1)
        self.play(FadeOut(mass_box), FadeOut(mass_label))

        # Highlight 'c^2' (speed of light squared)
        c_box = SurroundingRectangle(VGroup(eq[3], eq[4]), color=ACCENT_RED, buff=0.1)
        c_label = Text("speed of light squared", font_size=24,
                        color=ACCENT_RED).next_to(c_box, DOWN)
        self.play(Create(c_box), Write(c_label))
        self.wait(1)
        self.play(FadeOut(c_box), FadeOut(c_label))

        # Transform to show the implication
        eq2 = MathTex(
            "E", "=", "m", "\\cdot", "(3 \\times 10^8)^2",
            font_size=44
        )
        eq2[4].set_color(ACCENT_YELLOW)

        self.play(TransformMatchingTex(eq, eq2), run_time=2)
        self.wait(1)

        conclusion = MathTex(
            "E", "=", "m", "\\cdot", "9 \\times 10^{16}",
            font_size=44
        )
        conclusion[4].set_color(ACCENT_YELLOW)
        box = SurroundingRectangle(conclusion[4], color=ACCENT_YELLOW, buff=0.15)

        self.play(TransformMatchingTex(eq2, conclusion), run_time=1.5)
        self.play(Create(box))

        note = Text("A tiny mass = enormous energy!", font_size=24,
                      color=ACCENT_PINK).shift(DOWN * 1.5)
        self.play(FadeIn(note))
        self.wait(2)


class ValueTrackerMasterPattern(Scene):
    """The master pattern for ValueTracker + always_redraw.
    Shows the key technique used throughout 3b1b videos.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("ValueTracker + always_redraw Pattern", font_size=36,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        axes = Axes(
            x_range=[-4, 4, 1], y_range=[-2, 2, 0.5],
            x_length=8, y_length=3.5,
            axis_config={"color": TEXT_DIM, "stroke_width": 2}
        ).shift(DOWN * 0.3)
        self.play(Create(axes), run_time=1)

        # PATTERN 1: Dynamic graph controlled by ValueTracker
        freq = ValueTracker(1)
        amp = ValueTracker(1)

        dynamic_graph = always_redraw(lambda: axes.plot(
            lambda x: amp.get_value() * np.sin(freq.get_value() * x),
            x_range=[-4, 4],
            color=ACCENT_CYAN, stroke_width=3
        ))

        # PATTERN 2: Dynamic label
        param_display = always_redraw(lambda: VGroup(
            MathTex(f"A = {amp.get_value():.1f}", font_size=24, color=ACCENT_ORANGE),
            MathTex(f"\\omega = {freq.get_value():.1f}", font_size=24, color=ACCENT_GREEN),
        ).arrange(RIGHT, buff=1.0).to_edge(DOWN, buff=0.4))

        # PATTERN 3: Dynamic equation
        eq = always_redraw(lambda: MathTex(
            f"y = {amp.get_value():.1f}",
            r"\sin(",
            f"{freq.get_value():.1f}",
            r"x)",
            font_size=32, color=TEXT_PRIMARY
        ).shift(UP * 1.7))

        self.play(Create(dynamic_graph), FadeIn(param_display), Write(eq))
        self.wait(1)

        # Animate frequency change
        self.play(freq.animate.set_value(3), run_time=3, rate_func=smooth)
        self.wait(0.5)

        # Animate amplitude change
        self.play(amp.animate.set_value(1.5), run_time=2, rate_func=smooth)
        self.wait(0.5)

        # Animate both simultaneously
        self.play(
            freq.animate.set_value(0.5),
            amp.animate.set_value(0.5),
            run_time=3,
            rate_func=smooth
        )
        self.wait(0.5)

        # Reset
        self.play(
            freq.animate.set_value(1),
            amp.animate.set_value(1),
            run_time=2
        )
        self.wait(1)


class LaggedAnimationPatterns(Scene):
    """Demonstrates LaggedStartMap and other animation composition patterns
    used frequently in 3b1b videos for elegant multi-object animations.
    """

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Lagged Animation Patterns", font_size=42,
                      color=TEXT_PRIMARY, weight="BOLD").to_edge(UP, buff=0.3)
        self.play(Write(title))

        # PATTERN 1: LaggedStartMap with FadeIn
        dots = VGroup(*[
            Dot(radius=0.15, color=color)
            for color in [ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE,
                          ACCENT_RED, ACCENT_PURPLE, ACCENT_CYAN,
                          ACCENT_YELLOW, ACCENT_PINK]
        ]).arrange(RIGHT, buff=0.4).shift(UP * 1.0)

        label1 = Text("LaggedStartMap(FadeIn, ...)", font_size=20,
                        color=TEXT_DIM).shift(UP * 1.8)
        self.play(FadeIn(label1))
        self.play(LaggedStartMap(FadeIn, dots, lag_ratio=0.15), run_time=2)
        self.wait(0.5)

        # PATTERN 2: LaggedStartMap with GrowFromCenter
        squares = VGroup(*[
            Square(side_length=0.5, fill_opacity=0.7, fill_color=color,
                    stroke_width=0)
            for color in [ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE,
                          ACCENT_RED, ACCENT_PURPLE, ACCENT_CYAN]
        ]).arrange(RIGHT, buff=0.3).shift(DOWN * 0.2)

        label2 = Text("LaggedStartMap(GrowFromCenter, ...)", font_size=20,
                        color=TEXT_DIM).shift(DOWN * 0.9)
        self.play(FadeIn(label2))
        self.play(LaggedStartMap(GrowFromCenter, squares, lag_ratio=0.2), run_time=2)
        self.wait(0.5)

        # PATTERN 3: Successive transformations
        circle_row = VGroup(*[
            Circle(radius=0.3, fill_opacity=0.7, fill_color=ACCENT_BLUE,
                    stroke_width=0)
            for _ in range(6)
        ]).arrange(RIGHT, buff=0.3).shift(DOWN * 1.8)

        star_row = VGroup(*[
            Star(n=5, outer_radius=0.3, fill_opacity=0.7, fill_color=ACCENT_YELLOW,
                  stroke_width=0)
            for _ in range(6)
        ]).arrange(RIGHT, buff=0.3).shift(DOWN * 1.8)

        self.play(LaggedStartMap(FadeIn, circle_row, lag_ratio=0.1), run_time=1)
        self.wait(0.5)
        self.play(
            *[ReplacementTransform(c, s) for c, s in zip(circle_row, star_row)],
            lag_ratio=0.15, run_time=2
        )
        self.wait(2)
