"""
=============================================================================
COMPREHENSIVE MANIM CE PLOT & GRAPH ANIMATION REFERENCE
=============================================================================
Every interactive plot pattern, every parameter, every method — with complete
working code examples. Verified against Manim CE source.

Table of contents:
  1.  NumberLine — every parameter & method
  2.  Axes — every parameter, every method
  3.  NumberPlane — every configuration
  4.  PolarPlane — every configuration
  5.  ComplexPlane — every method
  6.  ThreeDAxes — full 3D coordinate system
  7.  CoordinateSystem methods — plot, area, riemann, tangent, etc.
  8.  ParametricFunction & FunctionGraph & ImplicitFunction
  9.  ValueTracker + always_redraw animated plots
  10. BarChart — every configuration and animation
  11. Multiple plots on same axes
  12. Parametric curves (2D)
  13. 3D plots (Surface, plot_surface)
  14. Statistical plots (histograms, box plots, scatter)
  15. Animated data changes (morphing between datasets)
  16. Scale classes (LinearBase, LogBase)

ALL CODE IS STANDALONE — each class is a renderable Scene.
"""

from manim import *
import numpy as np


# =============================================================================
# 1. NUMBER LINE — EVERY PARAMETER & METHOD
# =============================================================================

class NumberLineEveryParameter(Scene):
    """
    NumberLine(
        x_range=[x_min, x_max, x_step],  # default: [-frame_x_radius, frame_x_radius, 1]
        length=None,                       # total length in manim units; overrides unit_size
        unit_size=1,                       # distance between ticks; ignored if length set
        include_ticks=True,                # whether to show tick marks
        tick_size=0.1,                     # height of each tick
        numbers_with_elongated_ticks=None, # iterable of values with bigger ticks
        longer_tick_multiple=2,            # elongated tick = tick_size * this
        exclude_origin_tick=False,         # skip tick at 0 (used internally by Axes)
        rotation=0,                        # angle in radians to rotate the line
        stroke_width=2.0,                  # line thickness
        include_tip=False,                 # arrow tip at end
        tip_width=0.25,                    # tip width (DEFAULT_ARROW_TIP_LENGTH)
        tip_height=0.25,                   # tip height
        tip_shape=None,                    # custom ArrowTip class (e.g., StealthTip)
        include_numbers=False,             # auto-add labels
        font_size=36,                      # size of number labels
        label_direction=DOWN,              # where labels appear (UP, DOWN, LEFT, RIGHT)
        label_constructor=MathTex,         # class used for labels (MathTex, Tex, Text)
        scaling=LinearBase(),              # LogBase(base=10) for logarithmic
        line_to_number_buff=MED_SMALL_BUFF,# gap between line and label
        decimal_number_config=None,        # dict passed to DecimalNumber, e.g. {"num_decimal_places": 2}
        numbers_to_exclude=None,           # values to skip labeling
        numbers_to_include=None,           # explicit values to label
        color=WHITE,                       # stroke color (inherited from Line)
    )

    Key methods:
        number_to_point(number)   / n2p(number)     — value -> scene point
        point_to_number(point)    / p2n(point)       — scene point -> value
        add_ticks()                                   — adds tick marks
        get_tick(x, size)                             — returns a tick Line at x
        get_tick_range()                              — returns ndarray of tick positions
        add_numbers(x_values, excluding, font_size)   — adds DecimalNumber labels
        add_labels(dict_values, direction, buff)       — adds custom text labels
        get_number_mobject(x, direction, buff, font_size) — single positioned label
        rotate_about_zero(angle, axis)
        rotate_about_number(number, angle, axis)
        get_unit_size()                               — length / range
        get_unit_vector()

    Operator overloading:
        number_line @ 3          -> number_line.n2p(3)   -> point
        point @ number_line      -> number_line.p2n(point) -> float
    """

    def construct(self):
        # --- Basic number line ---
        nl_basic = NumberLine(
            x_range=[-5, 5, 1],
            length=10,
            color=BLUE,
            include_numbers=True,
            include_ticks=True,
            tick_size=0.1,
            font_size=24,
            label_direction=DOWN,
        )

        # --- Number line with elongated ticks ---
        nl_elongated = NumberLine(
            x_range=[-4, 4, 1],
            length=8,
            color=GREEN,
            include_numbers=True,
            numbers_with_elongated_ticks=[-2, 0, 2],
            longer_tick_multiple=3,
            font_size=20,
        ).shift(DOWN * 1.5)

        # --- With tip and decimal precision ---
        nl_tip = NumberLine(
            x_range=[0, 2, 0.25],
            length=8,
            include_tip=True,
            tip_width=0.2,
            tip_height=0.2,
            include_numbers=True,
            decimal_number_config={"num_decimal_places": 2},
            font_size=18,
            label_direction=UP,
        ).shift(UP * 1.5)

        # --- Rotated number line ---
        nl_rotated = NumberLine(
            x_range=[-3, 3, 1],
            length=5,
            rotation=30 * DEGREES,
            include_numbers=True,
            font_size=20,
            color=YELLOW,
        ).shift(DOWN * 3)

        self.add(nl_basic, nl_elongated, nl_tip, nl_rotated)

        # --- Method demonstrations ---
        # n2p: get scene coordinates for a value
        pt = nl_basic.n2p(3)
        dot = Dot(pt, color=RED)
        self.add(dot)

        # p2n: get value from scene point
        # value = nl_basic.p2n(dot.get_center())  # returns 3.0

        # @ operator
        pt2 = nl_basic @ (-2)  # same as nl_basic.n2p(-2)
        dot2 = Dot(pt2, color=ORANGE)
        self.add(dot2)


class NumberLineCustomLabels(Scene):
    """Demonstrates add_labels() with custom text labels."""

    def construct(self):
        nl = NumberLine(
            x_range=[0, 7, 1],
            length=10,
            include_ticks=True,
        )

        # Custom labels using a dict: {position: label_text}
        nl.add_labels(
            {
                1: "Mon",
                2: "Tue",
                3: "Wed",
                4: "Thu",
                5: "Fri",
                6: "Sat",
                7: "Sun",
            },
            direction=DOWN,
            buff=0.3,
            font_size=24,
        )
        self.add(nl)


class NumberLineLogarithmic(Scene):
    """Logarithmic number line using LogBase scaling."""

    def construct(self):
        nl = NumberLine(
            x_range=[0, 4, 1],     # exponents: 10^0 to 10^4
            length=10,
            scaling=LogBase(base=10, custom_labels=True),
            include_numbers=True,
            font_size=24,
        )
        self.add(nl)


class UnitIntervalExample(Scene):
    """UnitInterval: special NumberLine from 0 to 1."""

    def construct(self):
        ui = UnitInterval(
            unit_size=10,
            numbers_with_elongated_ticks=[0, 0.5, 1],
            decimal_number_config={"num_decimal_places": 1},
            include_numbers=True,
        )
        self.add(ui)


# =============================================================================
# 2. AXES — EVERY PARAMETER, EVERY METHOD
# =============================================================================

class AxesEveryParameter(Scene):
    """
    Axes(
        x_range=[x_min, x_max, x_step],  # default: [-7, 7, 1]
        y_range=[y_min, y_max, y_step],  # default: [-4, 4, 1]
        x_length=12,                      # width in manim units (frame_width - 2)
        y_length=6,                       # height in manim units (frame_height - 2)
        axis_config={},                   # dict passed to BOTH NumberLine axes
        x_axis_config={},                 # overrides for x-axis only
        y_axis_config={},                 # overrides for y-axis only
        tips=True,                        # include arrow tips on both axes
    )

    axis_config can include ANY NumberLine parameter:
        include_ticks, tick_size, include_numbers, font_size,
        include_tip, numbers_to_exclude, scaling, etc.

    Axes inherits from CoordinateSystem and VGroup.
    """

    def construct(self):
        ax = Axes(
            x_range=[0, 10, 1],
            y_range=[-2, 8, 1],
            x_length=10,
            y_length=5,
            tips=True,
            axis_config={
                "color": GREY_B,
                "stroke_width": 2,
                "include_ticks": True,
                "tick_size": 0.08,
                "font_size": 20,
                "include_numbers": True,
                "numbers_to_exclude": [0],
            },
            x_axis_config={
                "numbers_to_include": np.arange(0, 11, 2),
            },
            y_axis_config={
                "label_direction": LEFT,
                "numbers_to_include": np.arange(-2, 9, 2),
            },
        )
        self.add(ax)


class AxesAllMethods(Scene):
    """
    CoordinateSystem / Axes methods:

    COORDINATE CONVERSION:
        coords_to_point(x, y[, z])  / c2p(x, y)     — axis coords -> scene point
        point_to_coords(point)      / p2c(point)     — scene point -> axis coords
        @ operator:  ax @ (x, y)  = ax.c2p(x, y)
        get_origin()                                   — scene point of (0, 0)
        get_x_unit_size() / get_y_unit_size()

    AXIS ACCESS:
        get_axes()          — VGroup of axis NumberLines
        get_x_axis()        — x NumberLine
        get_y_axis()        — y NumberLine
        get_axis(index)     — axis by index

    LABELS:
        get_axis_labels(x_label="x", y_label="y")
        get_x_axis_label(label, edge=UR, direction=UR, buff=SMALL_BUFF)
        get_y_axis_label(label, edge=UR, direction=UP*0.5+RIGHT, buff=SMALL_BUFF)
        add_coordinates(*axes_numbers)  — add tick labels to axes

    GRAPHING:
        plot(function, x_range, use_vectorized, colorscale, colorscale_axis)
        plot_line_graph(x_values, y_values, z_values, line_color, add_vertex_dots, ...)
        plot_parametric_curve(function, use_vectorized, t_range, ...)
        plot_polar_graph(r_func, theta_range)
        plot_implicit_curve(func, min_depth, max_quads)
        plot_surface(function, u_range, v_range, colorscale, colorscale_axis)  [3D only]

    GRAPH HELPERS:
        input_to_graph_point(x, graph)  / i2gp(x, graph)  — x -> point on curve
        input_to_graph_coords(x, graph) / i2gc(x, graph)  — x -> (x, f(x))
        get_graph_label(graph, label, x_val, direction, buff, color, dot, dot_config)

    LINES:
        get_vertical_line(point)
        get_horizontal_line(point)
        get_lines_to_point(point)
        get_vertical_lines_to_graph(graph, x_range, num_lines)
        get_line_from_axis_to_point(index, point, line_func, line_config, color, stroke_width)

    CALCULUS:
        get_area(graph, x_range, color, opacity, bounded_graph)
        get_riemann_rectangles(graph, x_range, dx, input_sample_type, ...)
        angle_of_tangent(x, graph, dx)
        slope_of_tangent(x, graph)
        plot_derivative_graph(graph, color)
        plot_antiderivative_graph(graph, y_intercept, samples)
        get_secant_slope_group(x, graph, dx, dx_line_color, ...)

    MARKERS:
        get_T_label(x_val, graph, label, triangle_size, triangle_color, line_color)
    """

    def construct(self):
        ax = Axes(
            x_range=[-2, 6, 1],
            y_range=[-1, 8, 1],
            x_length=9,
            y_length=5.5,
            tips=True,
        )
        labels = ax.get_axis_labels(
            x_label=MathTex("x"),
            y_label=MathTex("y"),
        )
        ax.add_coordinates()
        self.add(ax, labels)

        # --- plot() ---
        curve = ax.plot(lambda x: 0.5 * x ** 2, color=BLUE, x_range=[0, 4])
        self.add(curve)

        # --- get_graph_label() ---
        lbl = ax.get_graph_label(
            curve,
            label=MathTex(r"\frac{1}{2}x^2"),
            x_val=3,
            direction=UR,
            buff=0.2,
            dot=True,
            dot_config={"color": YELLOW},
        )
        self.add(lbl)

        # --- get_vertical_line() ---
        v_line = ax.get_vertical_line(
            ax.i2gp(2, curve),
            line_config={"dashed_ratio": 0.85},
            color=YELLOW,
        )
        self.add(v_line)

        # --- get_horizontal_line() ---
        h_line = ax.get_horizontal_line(
            ax.i2gp(2, curve),
            line_func=DashedLine,
            color=GREEN,
        )
        self.add(h_line)

        # --- get_lines_to_point() ---
        lines = ax.get_lines_to_point(ax.c2p(3, 4.5), color=RED)
        self.add(lines)


# =============================================================================
# 2a. Axes.plot() — EVERY PARAMETER IN DETAIL
# =============================================================================

class AxesPlotEveryParameter(Scene):
    """
    ax.plot(
        function,                  # callable: float -> float
        x_range=None,              # [x_min, x_max, x_step] overrides axes range
        use_vectorized=False,      # pass entire t array to function
        colorscale=None,           # list of colors OR list of (color, pivot) tuples
        colorscale_axis=1,         # 0=x, 1=y for color mapping
        # Plus ANY ParametricFunction kwargs:
        color=YELLOW,
        stroke_width=2,
        use_smoothing=True,
        discontinuities=[],        # x values where function is discontinuous
        dt=1e-8,                   # tolerance around discontinuities
    )
    """

    def construct(self):
        ax = Axes(x_range=[-4, 4, 1], y_range=[-2, 4, 1], x_length=10, y_length=5)
        self.add(ax)

        # Basic plot
        g1 = ax.plot(lambda x: x ** 2, color=BLUE)
        self.add(g1)

        # With custom x_range and step
        g2 = ax.plot(lambda x: np.sin(x), x_range=[-4, 4, 0.01], color=RED)
        self.add(g2)

        # With colorscale by y-value
        g3 = ax.plot(
            lambda x: np.cos(x),
            x_range=[-4, 4, 0.01],
            colorscale=[BLUE, GREEN, YELLOW, RED],
            colorscale_axis=1,  # color by y-value
        )
        # self.add(g3)

        # With colorscale by x-value using pivot tuples
        g4 = ax.plot(
            lambda x: 0.5 * x,
            x_range=[-4, 4, 0.01],
            colorscale=[(BLUE, -4), (GREEN, 0), (RED, 4)],
            colorscale_axis=0,  # color by x-value
        )
        # self.add(g4)

        # Discontinuous function
        g5 = ax.plot(
            lambda x: (x ** 2 - 2) / (x ** 2 - 4),
            x_range=[-3.9, 3.9],
            discontinuities=[-2, 2],
            dt=0.1,
            color=ORANGE,
        )
        self.add(g5)


# =============================================================================
# 2b. plot_line_graph() — EVERY PARAMETER
# =============================================================================

class PlotLineGraphEveryParameter(Scene):
    """
    ax.plot_line_graph(
        x_values,                     # iterable of x coords
        y_values,                     # iterable of y coords
        z_values=None,                # iterable of z coords (0 if None)
        line_color=YELLOW,            # color of the line
        add_vertex_dots=True,         # add dots at each data point
        vertex_dot_radius=DEFAULT_DOT_RADIUS,
        vertex_dot_style={},          # dict: stroke_width, fill_color, etc.
        # Plus VMobject kwargs: stroke_width, stroke_opacity, etc.
    )

    Returns VDict with keys:
        "line_graph"  — the line VGroup
        "vertex_dots" — the dot VGroup (if add_vertex_dots=True)
    """

    def construct(self):
        ax = Axes(
            x_range=[0, 7, 1],
            y_range=[0, 6, 1],
            x_length=9,
            y_length=5,
            axis_config={"include_numbers": True},
        )
        self.add(ax)

        line_graph = ax.plot_line_graph(
            x_values=[0, 1, 2, 3, 4, 5, 6],
            y_values=[1, 3, 2, 5, 4, 3.5, 5.5],
            line_color=GOLD_E,
            add_vertex_dots=True,
            vertex_dot_radius=0.08,
            vertex_dot_style={"stroke_width": 2, "fill_color": PURPLE},
            stroke_width=3,
        )
        self.add(line_graph)

        # Access components:
        # line_graph["line_graph"]  -> the line
        # line_graph["vertex_dots"] -> the dots


# =============================================================================
# 2c. get_area() — EVERY PARAMETER
# =============================================================================

class GetAreaEveryParameter(Scene):
    """
    ax.get_area(
        graph,                        # ParametricFunction from ax.plot()
        x_range=None,                 # (x_min, x_max); defaults to graph range
        color=(BLUE, GREEN),          # single color or gradient tuple
        opacity=0.3,                  # fill opacity
        bounded_graph=None,           # second curve to bound between
    )
    Returns a Polygon.
    """

    def construct(self):
        ax = Axes(x_range=[-1, 5, 1], y_range=[-1, 5, 1])
        self.add(ax)

        f1 = ax.plot(lambda x: np.sin(x) * 2 + 2, x_range=[0, 4], color=BLUE)
        f2 = ax.plot(lambda x: 0.5 * x, x_range=[0, 4], color=RED)
        self.add(f1, f2)

        # Area under f1
        area1 = ax.get_area(f1, x_range=(0.5, 3.5), color=(BLUE, GREEN), opacity=0.3)
        self.add(area1)

        # Area BETWEEN f1 and f2
        area2 = ax.get_area(
            f1,
            x_range=(1, 3),
            color=(ORANGE, YELLOW),
            opacity=0.5,
            bounded_graph=f2,
        )
        self.add(area2)


# =============================================================================
# 2d. get_riemann_rectangles() — EVERY PARAMETER
# =============================================================================

class GetRiemannRectanglesEveryParameter(Scene):
    """
    ax.get_riemann_rectangles(
        graph,                             # the curve
        x_range=None,                      # [x_min, x_max]; defaults to graph range
        dx=0.1,                            # width of each rectangle
        input_sample_type="left",          # "left", "right", or "center"
        stroke_width=1,                    # border thickness
        stroke_color=BLACK,                # border color
        fill_opacity=1,                    # rectangle opacity
        color=(BLUE, GREEN),               # single or gradient of fill colors
        show_signed_area=True,             # invert color below x-axis
        bounded_graph=None,                # second curve as lower bound
        blend=False,                       # set stroke_color = fill_color
        width_scale_factor=1.001,          # slight overlap to avoid gaps
    )
    Returns VGroup of Rectangles.
    """

    def construct(self):
        ax = Axes(x_range=[-1, 5, 1], y_range=[-2, 5, 1])
        self.add(ax)

        graph = ax.plot(lambda x: 0.5 * x ** 2 - 1, color=BLUE)
        self.add(graph)

        # Left Riemann sum
        rects_left = ax.get_riemann_rectangles(
            graph, x_range=[0, 4], dx=0.5,
            input_sample_type="left",
            color=(BLUE, GREEN),
            fill_opacity=0.6,
            stroke_width=1,
            stroke_color=WHITE,
        )
        self.add(rects_left)

        # Right Riemann sum (shifted to side for visibility)
        rects_right = ax.get_riemann_rectangles(
            graph, x_range=[0, 4], dx=0.5,
            input_sample_type="right",
            color=(RED, ORANGE),
            fill_opacity=0.4,
        )
        # self.add(rects_right)

        # Between two curves
        upper = ax.plot(lambda x: 2 * x, x_range=[0.5, 4], color=GREEN)
        bounded_rects = ax.get_riemann_rectangles(
            upper, bounded_graph=graph,
            x_range=[1, 3.5], dx=0.25,
            show_signed_area=False,
            color=(MAROON_A, PURPLE_D),
        )
        # self.add(upper, bounded_rects)


# =============================================================================
# 2e. get_secant_slope_group() — EVERY PARAMETER
# =============================================================================

class GetSecantSlopeGroupEveryParameter(Scene):
    """
    ax.get_secant_slope_group(
        x,                            # x-value where secant starts
        graph,                        # the curve
        dx=None,                      # horizontal change (default: range/10)
        dx_line_color=YELLOW,         # color of horizontal line
        dy_line_color=None,           # color of vertical line (default: graph color)
        dx_label=None,                # label for dx (str, float, or Mobject)
        dy_label=None,                # label for dy
        include_secant_line=True,     # show the secant line
        secant_line_color=GREEN,      # color of secant
        secant_line_length=10,        # length of secant line
    )
    Returns VGroup with attributes: dx_line, df_line, secant_line, dx_label, df_label
    """

    def construct(self):
        ax = Axes(x_range=[-1, 5, 1], y_range=[-1, 7, 1])
        graph = ax.plot(lambda x: 0.25 * x ** 2, color=BLUE)
        self.add(ax, graph)

        slopes = ax.get_secant_slope_group(
            x=2.0,
            graph=graph,
            dx=1.0,
            dx_line_color=GREEN_B,
            dy_line_color=RED_B,
            dx_label=Tex("dx = 1.0"),
            dy_label=MathTex("dy"),
            include_secant_line=True,
            secant_line_color=YELLOW,
            secant_line_length=6,
        )
        self.add(slopes)


# =============================================================================
# 2f. get_T_label() — EVERY PARAMETER
# =============================================================================

class GetTLabelEveryParameter(Scene):
    """
    ax.get_T_label(
        x_val,                       # x position along the curve
        graph,                       # the curve
        label=None,                  # label text (str, float, Mobject)
        label_color=None,            # color of label
        triangle_size=MED_SMALL_BUFF,# size of triangle marker
        triangle_color=WHITE,        # color of triangle
        line_func=Line,              # Line or DashedLine for vertical line
        line_color=YELLOW,           # color of vertical line
    )
    Returns VGroup with triangle, vertical line, and optional label.
    """

    def construct(self):
        ax = Axes(x_range=[-1, 8, 1], y_range=[-1, 6, 1])
        graph = ax.plot(lambda x: 0.5 * x, color=BLUE)
        self.add(ax, graph)

        t_label = ax.get_T_label(
            x_val=4,
            graph=graph,
            label=Tex("x=4"),
            label_color=ORANGE,
            triangle_size=0.2,
            triangle_color=YELLOW,
            line_func=DashedLine,
            line_color=GREEN,
        )
        self.add(t_label)


# =============================================================================
# 2g. Calculus methods — derivative, antiderivative, tangent
# =============================================================================

class CalculusMethods(Scene):
    """
    ax.angle_of_tangent(x, graph, dx=1e-8)  -> float (radians)
    ax.slope_of_tangent(x, graph)            -> float
    ax.plot_derivative_graph(graph, color=GREEN) -> ParametricFunction
    ax.plot_antiderivative_graph(graph, y_intercept=0, samples=50) -> ParametricFunction
    """

    def construct(self):
        ax = Axes(x_range=[-4, 4, 1], y_range=[-3, 10, 1], y_length=5)
        self.add(ax)

        # Original function
        f = ax.plot(lambda x: x ** 2, color=BLUE)
        f_label = ax.get_graph_label(f, "x^2", x_val=2)
        self.add(f, f_label)

        # Derivative: 2x
        f_prime = ax.plot_derivative_graph(f, color=GREEN)
        fp_label = ax.get_graph_label(f_prime, "2x", x_val=3, direction=RIGHT)
        self.add(f_prime, fp_label)

        # Antiderivative: x^3/3
        orig = ax.plot(lambda x: x ** 2, color=RED)
        anti = ax.plot_antiderivative_graph(orig, y_intercept=0, samples=100, color=YELLOW)
        # self.add(anti)


# =============================================================================
# 2h. get_vertical_lines_to_graph()
# =============================================================================

class GetVerticalLinesToGraphExample(Scene):
    """
    ax.get_vertical_lines_to_graph(
        graph,                # the curve
        x_range=None,         # [x_min, x_max]; defaults to axes range
        num_lines=20,         # number of evenly spaced lines
        color=BLUE,           # plus any get_vertical_line kwargs
    )
    """

    def construct(self):
        ax = Axes(x_range=[0, 8, 1], y_range=[-1, 1, 0.2])
        ax.add_coordinates()
        curve = ax.plot(lambda x: np.sin(x) / np.e ** 2 * x, color=BLUE)

        lines = ax.get_vertical_lines_to_graph(
            curve, x_range=[0, 6], num_lines=40, color=TEAL
        )
        self.add(ax, curve, lines)


# =============================================================================
# 2i. plot_implicit_curve()
# =============================================================================

class PlotImplicitCurveExample(Scene):
    """
    ax.plot_implicit_curve(
        func,              # f(x, y) = 0 defines the curve
        min_depth=5,       # minimum subdivision depth
        max_quads=1500,    # maximum quads for accuracy
        color=...,         # plus VMobject kwargs
    )
    """

    def construct(self):
        ax = Axes()
        self.add(ax)

        # Circle: x^2 + y^2 - 4 = 0
        circle = ax.plot_implicit_curve(
            lambda x, y: x ** 2 + y ** 2 - 4,
            color=YELLOW,
        )
        self.add(circle)

        # Cassini oval
        cassini = ax.plot_implicit_curve(
            lambda x, y: (x ** 2 + y ** 2) ** 2 - 2 * (x ** 2 - y ** 2) - 1,
            color=BLUE,
        )
        self.add(cassini)


# =============================================================================
# 3. NUMBER PLANE — EVERY CONFIGURATION
# =============================================================================

class NumberPlaneEveryParameter(Scene):
    """
    NumberPlane(
        x_range=(-7.1, 7.1, 1),       # horizontal range
        y_range=(-4.0, 4.0, 1),       # vertical range
        x_length=None,                  # auto-calculated if None (1 unit = 1 manim unit)
        y_length=None,                  # auto-calculated if None
        background_line_style={         # style for main grid lines
            "stroke_color": BLUE_D,
            "stroke_width": 2,
            "stroke_opacity": 1,
        },
        faded_line_style=None,          # auto: half of background_line_style
        faded_line_ratio=1,             # subdivisions: 2=4 boxes, 3=9 boxes per cell
        make_smooth_after_applying_functions=True,
        # Plus ALL Axes parameters (axis_config, tips, etc.)
    )

    Inherits from Axes. Has all Axes methods plus:
        get_vector(coords)                    -> Arrow from origin
        prepare_for_nonlinear_transform(n=50) -> subdivide curves for smooth transforms
    """

    def construct(self):
        plane = NumberPlane(
            x_range=(-5, 5, 1),
            y_range=(-3, 3, 1),
            x_length=10,
            y_length=6,
            background_line_style={
                "stroke_color": TEAL,
                "stroke_width": 2,
                "stroke_opacity": 0.5,
            },
            faded_line_ratio=2,  # 4 subdivisions per cell
            axis_config={
                "stroke_width": 2,
                "include_ticks": True,
                "include_numbers": True,
                "font_size": 20,
            },
        )
        self.add(plane)

        # get_vector
        vec = plane.get_vector([2, 1], color=YELLOW)
        self.add(vec)


class NumberPlaneNonlinearTransform(Scene):
    """Applying a nonlinear transform to a NumberPlane."""

    def construct(self):
        plane = NumberPlane()
        plane.prepare_for_nonlinear_transform(num_inserted_curves=50)
        self.add(plane)

        self.play(
            plane.animate.apply_function(
                lambda p: p + np.array([np.sin(p[1]), np.sin(p[0]), 0])
            ),
            run_time=3,
        )


# =============================================================================
# 4. POLAR PLANE — EVERY CONFIGURATION
# =============================================================================

class PolarPlaneEveryParameter(Scene):
    """
    PolarPlane(
        radius_max=4.0,                    # maximum radius
        size=None,                          # diameter; auto-calculated if None
        radius_step=1,                      # distance between radius lines
        azimuth_step=None,                  # divisions of the circle (auto from units)
        azimuth_units="PI radians",         # "PI radians", "TAU radians", "degrees", "gradians", None
        azimuth_compact_fraction=True,      # fraction formatting: xu/y vs x/y*u
        azimuth_offset=0,                   # rotation offset in radians
        azimuth_direction="CCW",            # "CCW" or "CW"
        azimuth_label_buff=SMALL_BUFF,      # distance of azimuth labels from circle
        azimuth_label_font_size=24,         # font size of azimuth labels
        radius_config={                     # NumberLine config for radius axis
            "stroke_width": 2,
            "include_ticks": False,
            "include_tip": False,
            "font_size": 24,
        },
        background_line_style={...},        # same as NumberPlane
        faded_line_style=None,
        faded_line_ratio=1,
    )

    Methods:
        add_coordinates(r_values=None, a_values=None)
        get_coordinate_labels(r_values, a_values) -> VDict
        polar_to_point(radius, azimuth) / pr2pt()
        point_to_polar(point) / pt2pr()
        plot_polar_graph(r_func, theta_range)
    """

    def construct(self):
        # PI radians labeling
        polar_pi = PolarPlane(
            azimuth_units="PI radians",
            size=5,
            radius_max=3,
            radius_step=1,
            azimuth_step=12,  # 12 divisions
            azimuth_label_font_size=20,
            radius_config={"font_size": 20, "include_numbers": True},
            background_line_style={
                "stroke_color": BLUE_D,
                "stroke_width": 1.5,
            },
        ).add_coordinates()
        self.add(polar_pi)


class PolarPlaneGraphing(Scene):
    """Plotting polar functions on PolarPlane."""

    def construct(self):
        plane = PolarPlane(size=5, radius_max=3).add_coordinates()
        self.add(plane)

        # Rose curve: r = 2*sin(5*theta)
        rose = plane.plot_polar_graph(
            lambda theta: 2 * np.sin(5 * theta),
            theta_range=[0, 2 * PI],
            color=ORANGE,
        )
        self.add(rose)

        # Cardioid: r = 1 + cos(theta)
        cardioid = plane.plot_polar_graph(
            lambda theta: 1 + np.cos(theta),
            theta_range=[0, 2 * PI],
            color=GREEN,
        )
        # self.add(cardioid)


# =============================================================================
# 5. COMPLEX PLANE — EVERY METHOD
# =============================================================================

class ComplexPlaneEveryMethod(Scene):
    """
    ComplexPlane inherits from NumberPlane.

    Extra methods:
        number_to_point(complex_number) / n2p()  — complex -> scene point
        point_to_number(point)          / p2n()  — scene point -> complex
        get_coordinate_labels(*numbers)           — labels for complex numbers
        add_coordinates(*numbers)
    """

    def construct(self):
        plane = ComplexPlane(
            x_range=[-4, 4, 1],
            y_range=[-3, 3, 1],
            x_length=8,
            y_length=6,
        ).add_coordinates()
        self.add(plane)

        # Plot complex numbers
        z1 = 2 + 1j
        z2 = -1 - 2j
        z3 = z1 * z2  # complex multiplication

        d1 = Dot(plane.n2p(z1), color=YELLOW)
        d2 = Dot(plane.n2p(z2), color=RED)
        d3 = Dot(plane.n2p(z3), color=GREEN)

        l1 = MathTex("2+i", font_size=24).next_to(d1, UR, 0.1)
        l2 = MathTex("-1-2i", font_size=24).next_to(d2, DL, 0.1)
        l3 = MathTex("z_1 z_2", font_size=24, color=GREEN).next_to(d3, UR, 0.1)

        self.add(d1, d2, d3, l1, l2, l3)


class ComplexPlaneAnimated(Scene):
    """ComplexValueTracker for animated complex number operations."""

    def construct(self):
        plane = ComplexPlane().add_coordinates()
        self.add(plane)

        tracker = ComplexValueTracker(-2 + 1j)
        dot = Dot(color=YELLOW).add_updater(
            lambda m: m.move_to(plane.n2p(tracker.get_value()))
        )
        label = always_redraw(
            lambda: MathTex(
                f"{tracker.get_value().real:.1f}+{tracker.get_value().imag:.1f}i",
                font_size=24,
            ).next_to(dot, UR, 0.1)
        )

        self.add(dot, label)
        self.play(tracker.animate.set_value(3 + 2j), run_time=2)
        self.play(tracker.animate.set_value(tracker.get_value() * 1j), run_time=2)


# =============================================================================
# 6. THREE-D AXES — FULL 3D COORDINATE SYSTEM
# =============================================================================

class ThreeDAxesEveryParameter(ThreeDScene):
    """
    ThreeDAxes(
        x_range=(-6, 6, 1),
        y_range=(-5, 5, 1),
        z_range=(-4, 4, 1),
        x_length=10.5,                # frame_height + 2.5
        y_length=10.5,
        z_length=6.5,                 # frame_height - 1.5
        z_axis_config=None,           # dict for z-axis NumberLine
        z_normal=DOWN,                # normal direction of z-axis
        num_axis_pieces=20,           # pieces for 3D shading
        light_source=9*DOWN + 7*LEFT + 10*OUT,
    )

    Extra methods (over Axes):
        get_z_axis()
        get_z_axis_label(label, edge=OUT, direction=RIGHT, buff, rotation, rotation_axis)
        get_axis_labels(x_label, y_label, z_label)
    """

    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)

        axes = ThreeDAxes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            z_range=(-2, 2, 1),
            x_length=8,
            y_length=8,
            z_length=4,
        )
        labels = axes.get_axis_labels(
            x_label=MathTex("x"),
            y_label=MathTex("y"),
            z_label=MathTex("z"),
        )
        self.add(axes, labels)


# =============================================================================
# 7. COORDINATE SYSTEM METHODS — plot_parametric_curve, plot_polar_graph
# =============================================================================

class PlotParametricCurveExample(Scene):
    """
    ax.plot_parametric_curve(
        function,              # callable: t -> (x, y[, z])
        use_vectorized=False,
        t_range=[0, 2*PI],    # via ParametricFunction kwargs
        color=...,
    )
    """

    def construct(self):
        ax = Axes()
        self.add(ax)

        # Cardioid
        cardioid = ax.plot_parametric_curve(
            lambda t: np.array([
                np.exp(1) * np.cos(t) * (1 - np.cos(t)),
                np.exp(1) * np.sin(t) * (1 - np.cos(t)),
                0,
            ]),
            t_range=[0, 2 * PI],
            color=RED,
        )
        self.add(cardioid)

        # Lemniscate of Bernoulli
        lemniscate = ax.plot_parametric_curve(
            lambda t: np.array([
                2 * np.cos(t) / (1 + np.sin(t) ** 2),
                2 * np.cos(t) * np.sin(t) / (1 + np.sin(t) ** 2),
                0,
            ]),
            t_range=[0, 2 * PI],
            color=GREEN,
        )
        self.add(lemniscate)


# =============================================================================
# 8. PARAMETRIC FUNCTION, FUNCTION GRAPH, IMPLICIT FUNCTION
# =============================================================================

class ParametricFunctionEveryParameter(Scene):
    """
    ParametricFunction(
        function,              # callable: t -> (x, y, z) or point-like
        t_range=(0, 1, 0.01), # (t_min, t_max, t_step)
        scaling=LinearBase(),  # scaling class
        dt=1e-8,               # tolerance for discontinuities
        discontinuities=None,  # iterable of t values
        use_smoothing=True,    # smooth Bezier interpolation
        use_vectorized=False,  # pass array of t values
        # VMobject kwargs: color, stroke_width, fill_opacity, etc.
    )

    Methods:
        get_function()              -> the wrapped function
        get_point_from_function(t)  -> point at parameter t
    """

    def construct(self):
        # 2D parametric: Lissajous
        lissajous = ParametricFunction(
            lambda t: np.array([np.sin(3 * t), np.sin(2 * t), 0]),
            t_range=[0, 2 * PI, 0.01],
            color=RED,
            stroke_width=3,
        ).scale(2)
        self.add(lissajous)


class FunctionGraphEveryParameter(Scene):
    """
    FunctionGraph(
        function,              # callable: x -> y
        x_range=None,          # (x_min, x_max[, x_step]); defaults to frame width
        color=YELLOW,
        # Plus all ParametricFunction kwargs
    )

    This is a standalone graph (NOT on axes). It maps directly to scene coords.
    For plotting on Axes, use ax.plot() instead.
    """

    def construct(self):
        g1 = FunctionGraph(
            lambda x: np.sin(x),
            x_range=[-PI, PI],
            color=BLUE,
        )
        g2 = FunctionGraph(
            lambda x: np.cos(x),
            x_range=[-PI, PI],
            color=RED,
        )
        self.add(g1, g2)


class ImplicitFunctionEveryParameter(Scene):
    """
    ImplicitFunction(
        func,                  # callable: (x, y) -> float; curve where f(x,y)=0
        x_range=None,          # [x_min, x_max]; defaults to frame width
        y_range=None,          # [y_min, y_max]; defaults to frame height
        min_depth=5,           # minimum recursive subdivision depth
        max_quads=1500,        # max quads for resolution
        use_smoothing=True,    # smooth the resulting curve
        # VMobject kwargs: color, stroke_width, etc.
    )
    """

    def construct(self):
        plane = NumberPlane()
        self.add(plane)

        # Circle
        circle = ImplicitFunction(
            lambda x, y: x ** 2 + y ** 2 - 4,
            color=YELLOW,
        )
        # Hyperbola
        hyperbola = ImplicitFunction(
            lambda x, y: x ** 2 - y ** 2 - 1,
            color=RED,
        )
        self.add(circle, hyperbola)


# =============================================================================
# 9. VALUE TRACKER + ALWAYS_REDRAW — ANIMATED PLOTS
# =============================================================================

class ValueTrackerReference(Scene):
    """
    ValueTracker(value=0)

    Methods:
        get_value()           -> float
        set_value(value)      -> self
        increment_value(dv)   -> self

    Arithmetic operators:
        tracker += 1       (iadd)
        tracker -= 1       (isub)
        tracker *= 2       (imul)
        tracker /= 2       (itruediv)
        tracker //= 2      (ifloordiv)
        tracker %= 3       (imod)
        tracker **= 2      (ipow)
        tracker + 1        (add) -> new ValueTracker
        tracker - 1        (sub) -> new ValueTracker
        etc.

    Animation:
        self.play(tracker.animate.set_value(5))
        self.play(tracker.animate.increment_value(2))

    Updater-based (continuous):
        tracker.add_updater(lambda m, dt: m.increment_value(dt))

    ComplexValueTracker(value=0+0j)
        get_value()  -> complex
        set_value(z) -> self
        # Also animatable via .animate
    """

    def construct(self):
        nl = NumberLine(x_range=[-5, 5, 1], include_numbers=True)
        tracker = ValueTracker(0)
        pointer = Triangle(fill_opacity=1, color=YELLOW).scale(0.2).rotate(PI)
        pointer.add_updater(
            lambda m: m.next_to(nl.n2p(tracker.get_value()), UP, buff=0.1)
        )
        label = DecimalNumber(0, font_size=30).add_updater(
            lambda m: m.set_value(tracker.get_value()).next_to(pointer, UP, buff=0.1)
        )

        self.add(nl, pointer, label)
        self.play(tracker.animate.set_value(4), run_time=2)
        self.play(tracker.animate.set_value(-3), run_time=2)
        self.play(tracker.animate.set_value(0), run_time=1)


# --- 9a: Moving dot along a curve ---

class MovingDotAlongCurve(Scene):
    """ValueTracker + always_redraw: dot sliding along a curve."""

    def construct(self):
        ax = Axes(x_range=[-1, 7, 1], y_range=[-1, 5, 1], x_length=10, y_length=5)
        curve = ax.plot(lambda x: np.sqrt(x), color=BLUE, x_range=[0, 6])
        self.add(ax, curve)

        t = ValueTracker(0.1)

        dot = always_redraw(
            lambda: Dot(ax.i2gp(t.get_value(), curve), color=YELLOW, radius=0.08)
        )

        # Tangent line at the dot
        tangent = always_redraw(
            lambda: ax.get_secant_slope_group(
                x=t.get_value(),
                graph=curve,
                dx=0.01,
                secant_line_length=3,
                secant_line_color=RED,
                include_secant_line=True,
            )
        )

        coord_label = always_redraw(
            lambda: MathTex(
                f"({t.get_value():.1f}, {np.sqrt(t.get_value()):.2f})",
                font_size=20,
            ).next_to(ax.i2gp(t.get_value(), curve), UR, buff=0.15)
        )

        self.add(dot, tangent, coord_label)
        self.play(t.animate.set_value(6), run_time=5, rate_func=linear)


# --- 9b: Growing/shrinking area under curve ---

class GrowingShrinkingArea(Scene):
    """ValueTracker controlling the upper bound of an area fill."""

    def construct(self):
        ax = Axes(x_range=[-0.5, 5, 1], y_range=[-0.5, 4, 1])
        func = lambda x: np.sin(x) + 1.5
        curve = ax.plot(func, x_range=[0, 4.5], color=BLUE)
        self.add(ax, curve)

        upper = ValueTracker(0.1)

        area = always_redraw(
            lambda: ax.get_area(
                curve,
                x_range=[0, max(0.01, upper.get_value())],
                color=(BLUE, GREEN),
                opacity=0.4,
            )
        )

        area_text = always_redraw(
            lambda: MathTex(
                f"x = {upper.get_value():.1f}",
                font_size=28, color=YELLOW,
            ).to_corner(UR)
        )

        self.add(area, area_text)
        self.play(upper.animate.set_value(4.5), run_time=4, rate_func=linear)
        self.play(upper.animate.set_value(1), run_time=2)
        self.play(upper.animate.set_value(4.5), run_time=2)


# --- 9c: Animated tangent line ---

class AnimatedTangentLine(Scene):
    """Tangent line sliding along a curve using ValueTracker."""

    def construct(self):
        ax = Axes(x_range=[-4, 4, 1], y_range=[-2, 5, 1])
        curve = ax.plot(lambda x: 0.25 * x ** 3 - x, color=BLUE)
        self.add(ax, curve)

        x_val = ValueTracker(-3)

        tangent_line = always_redraw(
            lambda: TangentLine(
                curve,
                alpha=self._x_to_alpha(x_val.get_value(), -4, 4),
                length=4,
                color=YELLOW,
                stroke_width=3,
            )
        )

        dot = always_redraw(
            lambda: Dot(
                ax.i2gp(x_val.get_value(), curve),
                color=RED, radius=0.08,
            )
        )

        slope_label = always_redraw(
            lambda: MathTex(
                f"m = {ax.slope_of_tangent(x_val.get_value(), curve):.2f}",
                font_size=24, color=YELLOW,
            ).to_corner(UR)
        )

        self.add(tangent_line, dot, slope_label)
        self.play(x_val.animate.set_value(3), run_time=5, rate_func=linear)

    @staticmethod
    def _x_to_alpha(x, x_min, x_max):
        """Convert x-value to proportion along curve [0, 1]."""
        return np.clip((x - x_min) / (x_max - x_min), 0.001, 0.999)


# --- 9d: Dynamic function plotting (changing parameters) ---

class DynamicFunctionPlotting(Scene):
    """Animating function parameters: f(x) = A*sin(Bx + C)."""

    def construct(self):
        ax = Axes(
            x_range=[-2 * PI, 2 * PI, PI / 2],
            y_range=[-3, 3, 1],
            x_length=10,
            y_length=5,
        )
        self.add(ax)

        A = ValueTracker(1)
        B = ValueTracker(1)
        C = ValueTracker(0)

        graph = always_redraw(
            lambda: ax.plot(
                lambda x: A.get_value() * np.sin(B.get_value() * x + C.get_value()),
                color=BLUE,
                stroke_width=3,
            )
        )

        param_label = always_redraw(
            lambda: VGroup(
                MathTex(f"A = {A.get_value():.2f}", font_size=24, color=RED),
                MathTex(f"B = {B.get_value():.2f}", font_size=24, color=GREEN),
                MathTex(f"C = {C.get_value():.2f}", font_size=24, color=YELLOW),
            ).arrange(DOWN, aligned_edge=LEFT).to_corner(UR)
        )

        self.add(graph, param_label)

        # Animate amplitude
        self.play(A.animate.set_value(2), run_time=2)
        self.play(A.animate.set_value(0.5), run_time=2)
        self.play(A.animate.set_value(1), run_time=1)

        # Animate frequency
        self.play(B.animate.set_value(3), run_time=2)
        self.play(B.animate.set_value(1), run_time=1)

        # Animate phase shift
        self.play(C.animate.set_value(PI), run_time=2)
        self.play(C.animate.set_value(0), run_time=1)


# --- 9e: Animated Riemann sum (decreasing dx) ---

class AnimatedRiemannSum(Scene):
    """ValueTracker controlling dx of Riemann rectangles."""

    def construct(self):
        ax = Axes(x_range=[-0.5, 4.5, 1], y_range=[-0.5, 5, 1])
        func = lambda x: 0.5 * x ** 2
        curve = ax.plot(func, x_range=[0, 4], color=BLUE)
        self.add(ax, curve)

        dx_tracker = ValueTracker(1.0)

        rects = always_redraw(
            lambda: ax.get_riemann_rectangles(
                curve,
                x_range=[0, 4],
                dx=max(0.05, dx_tracker.get_value()),
                color=(BLUE, GREEN),
                fill_opacity=0.5,
                stroke_width=0.5,
            )
        )

        dx_label = always_redraw(
            lambda: MathTex(
                rf"\Delta x = {dx_tracker.get_value():.2f}",
                font_size=28, color=ORANGE,
            ).to_corner(UR)
        )

        self.add(rects, dx_label)
        self.play(dx_tracker.animate.set_value(0.05), run_time=5, rate_func=linear)


# =============================================================================
# 10. BAR CHART — EVERY CONFIGURATION AND ANIMATION
# =============================================================================

class BarChartEveryParameter(Scene):
    """
    BarChart(
        values,                            # list of floats (bar heights)
        bar_names=None,                    # list of strings (x-axis labels)
        y_range=None,                      # [y_min, y_max, y_step]; auto-calculated if None
        x_length=None,                     # auto-calculated if None
        y_length=None,                     # frame_height - 4 if None
        bar_colors=["#003f5c","#58508d","#bc5090","#ff6361","#ffa600"],
        bar_width=0.6,                     # 0 < bar_width <= 1
        bar_fill_opacity=0.7,
        bar_stroke_width=3,
        x_axis_config={"font_size": 24, "label_constructor": Tex},
        y_axis_config={},
        tips=False,                        # arrow tips on axes (default False for BarChart)
    )

    Attributes:
        chart.bars         — VGroup of Rectangle bars
        chart.x_labels     — VGroup of x-axis labels (if bar_names provided)
        chart.values       — the values list

    Methods:
        change_bar_values(values, update_colors=True)
        get_bar_labels(color=None, font_size=24, buff=MED_SMALL_BUFF, label_constructor=Tex)

    Inherits ALL Axes methods (plot, c2p, etc.)
    """

    def construct(self):
        chart = BarChart(
            values=[10, 25, -5, 40, 30, 15],
            bar_names=["A", "B", "C", "D", "E", "F"],
            y_range=[-10, 50, 10],
            x_length=10,
            y_length=5,
            bar_colors=[BLUE, TEAL, GREEN, YELLOW, ORANGE, RED],
            bar_width=0.7,
            bar_fill_opacity=0.8,
            bar_stroke_width=2,
            x_axis_config={"font_size": 28},
            y_axis_config={"font_size": 20, "include_numbers": True},
        )

        bar_labels = chart.get_bar_labels(
            color=WHITE,
            font_size=20,
            buff=0.15,
            label_constructor=Tex,
        )

        self.add(chart, bar_labels)


class BarChartAnimations(Scene):
    """Complete bar chart animation workflow."""

    def construct(self):
        # --- Create chart ---
        chart = BarChart(
            values=[0, 0, 0, 0, 0],  # start empty
            bar_names=["v1", "v2", "v3", "v4", "v5"],
            y_range=[0, 100, 20],
            bar_colors=[BLUE, GREEN, YELLOW, ORANGE, RED],
        )
        self.play(Create(chart), run_time=1)

        # --- Grow bars to target values ---
        target = chart.copy()
        target.change_bar_values([72, 85, 91, 68, 95])
        self.play(chart.animate.become(target), run_time=2)
        chart.values = [72, 85, 91, 68, 95]  # sync internal state

        # --- Add labels ---
        labels = chart.get_bar_labels(font_size=24)
        self.play(FadeIn(labels))
        self.wait(1)

        # --- Morph to new dataset ---
        self.play(FadeOut(labels))
        new_target = chart.copy()
        new_target.change_bar_values([88, 78, 96, 82, 90])
        self.play(chart.animate.become(new_target), run_time=2)
        chart.values = [88, 78, 96, 82, 90]

        new_labels = chart.get_bar_labels(font_size=24)
        self.play(FadeIn(new_labels))
        self.wait(1)

        # --- Highlight a bar ---
        highlight = SurroundingRectangle(chart.bars[2], color=YELLOW, buff=0.05)
        self.play(Create(highlight))
        self.play(Indicate(chart.bars[2], color=YELLOW))
        self.wait(1)


class BarChartWithChangeBarValues(Scene):
    """Using change_bar_values() directly (instant, no animation)."""

    def construct(self):
        chart = BarChart(
            values=[-10, -8, -6, -4, -2, 0, 2, 4, 6, 8, 10],
            y_range=[-10, 10, 2],
            y_axis_config={"font_size": 20},
        )
        self.add(chart)

        # Reverse the values
        chart.change_bar_values(list(reversed(chart.values)))
        labels = chart.get_bar_labels(font_size=20)
        self.add(labels)


# =============================================================================
# 11. MULTIPLE PLOTS ON SAME AXES
# =============================================================================

class MultiplePlotsOnSameAxes(Scene):
    """Overlay several functions on one set of axes with a legend."""

    def construct(self):
        ax = Axes(
            x_range=[-2 * PI, 2 * PI, PI / 2],
            y_range=[-2, 2, 0.5],
            x_length=10,
            y_length=5,
            axis_config={"include_numbers": False, "color": GREY_B},
        )
        ax.add_coordinates()
        self.add(ax)

        # Multiple functions
        sin_g = ax.plot(lambda x: np.sin(x), color=BLUE, stroke_width=3)
        cos_g = ax.plot(lambda x: np.cos(x), color=RED, stroke_width=3)
        sincos_g = ax.plot(lambda x: np.sin(x) * np.cos(x), color=GREEN, stroke_width=3)
        self.add(sin_g, cos_g, sincos_g)

        # Graph labels
        sin_lbl = ax.get_graph_label(sin_g, r"\sin x", x_val=PI, direction=UR)
        cos_lbl = ax.get_graph_label(cos_g, r"\cos x", x_val=-PI, direction=UR)
        sincos_lbl = ax.get_graph_label(sincos_g, r"\sin x \cos x", x_val=PI / 4, direction=UR)
        self.add(sin_lbl, cos_lbl, sincos_lbl)

        # Area between sin and cos
        area = ax.get_area(
            sin_g,
            x_range=[0, PI / 4],
            bounded_graph=cos_g,
            color=YELLOW,
            opacity=0.3,
        )
        self.add(area)


class MultiplePlotsWithColorscale(Scene):
    """Using colorscale to color-code a single curve by value."""

    def construct(self):
        ax = Axes(x_range=[-4, 4, 1], y_range=[-2, 2, 0.5], x_length=10, y_length=5)
        self.add(ax)

        # Color by y-value
        g = ax.plot(
            lambda x: np.sin(x),
            x_range=[-4, 4, 0.01],
            colorscale=[BLUE, WHITE, RED],
            colorscale_axis=1,
        )
        self.add(g)


# =============================================================================
# 12. PARAMETRIC CURVES (2D) — complete patterns
# =============================================================================

class ParametricCurvePatterns(Scene):
    """Collection of parametric curve patterns."""

    def construct(self):
        ax = Axes(x_range=[-4, 4, 1], y_range=[-3, 3, 1])
        self.add(ax)

        # --- Epicycloid ---
        R, r = 3, 1
        epicycloid = ax.plot_parametric_curve(
            lambda t: np.array([
                (R + r) * np.cos(t) - r * np.cos((R + r) / r * t),
                (R + r) * np.sin(t) - r * np.sin((R + r) / r * t),
                0,
            ]),
            t_range=[0, 2 * PI],
            color=RED,
        )
        # self.add(epicycloid)

        # --- Hypotrochoid (Spirograph) ---
        R2, r2, d = 5, 3, 2
        spirograph = ax.plot_parametric_curve(
            lambda t: np.array([
                (R2 - r2) * np.cos(t) + d * np.cos((R2 - r2) / r2 * t),
                (R2 - r2) * np.sin(t) - d * np.sin((R2 - r2) / r2 * t),
                0,
            ]),
            t_range=[0, 6 * PI, 0.01],
            color=TEAL,
        )
        self.add(spirograph)

        # --- Butterfly curve ---
        butterfly = ParametricFunction(
            lambda t: np.array([
                np.sin(t) * (np.exp(np.cos(t)) - 2 * np.cos(4 * t) - np.sin(t / 12) ** 5),
                np.cos(t) * (np.exp(np.cos(t)) - 2 * np.cos(4 * t) - np.sin(t / 12) ** 5),
                0,
            ]),
            t_range=[0, 12 * PI, 0.01],
            color=PURPLE,
            stroke_width=1.5,
        ).scale(0.4)
        # self.add(butterfly)


class AnimatedParametricCurve(Scene):
    """Tracing a parametric curve with a moving dot."""

    def construct(self):
        ax = Axes(x_range=[-3, 3, 1], y_range=[-3, 3, 1])
        self.add(ax)

        t_val = ValueTracker(0.01)

        # Parametric function: rose curve in Cartesian
        def rose_xy(t):
            r = 2 * np.cos(3 * t)
            return np.array([r * np.cos(t), r * np.sin(t), 0])

        traced = always_redraw(
            lambda: ParametricFunction(
                lambda t: ax.c2p(*rose_xy(t)[:2]),
                t_range=[0, t_val.get_value()],
                color=ORANGE,
                stroke_width=3,
            )
        )

        dot = always_redraw(
            lambda: Dot(
                ax.c2p(*rose_xy(t_val.get_value())[:2]),
                color=YELLOW, radius=0.06,
            )
        )

        self.add(traced, dot)
        self.play(t_val.animate.set_value(PI), run_time=4, rate_func=linear)


# =============================================================================
# 13. 3D PLOTS — Surface, plot_surface
# =============================================================================

class SurfaceEveryParameter(ThreeDScene):
    """
    Surface(
        func,                              # callable: (u, v) -> (x, y, z) ndarray
        u_range=(0, 1),                    # (u_min, u_max)
        v_range=(0, 1),                    # (v_min, v_max)
        resolution=32,                     # int or (u_res, v_res) tuple
        fill_color=BLUE_D,
        fill_opacity=1.0,
        checkerboard_colors=[BLUE_D, BLUE_E],  # alternating face colors; False to disable
        stroke_color=LIGHT_GREY,
        stroke_width=0.5,
        should_make_jagged=False,          # jagged vs smooth Bezier

        surface_piece_config={},           # dict for individual face VMobjects
        pre_function_handle_to_anchor_scale_factor=0.00001,
    )

    Methods:
        set_fill_by_checkerboard(*colors, opacity=None)
        set_fill_by_value(axes, colorscale, axis=2)  # color by axis value
    """

    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=-60 * DEGREES)

        axes = ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[-2, 2, 1])
        self.add(axes)

        # --- Basic surface ---
        surface = Surface(
            lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(24, 24),
            fill_opacity=0.8,
            checkerboard_colors=[BLUE_D, BLUE_E],
            stroke_color=WHITE,
            stroke_width=0.3,
        )
        self.add(surface)


class SurfaceColorByValue(ThreeDScene):
    """Surface colored by z-value using set_fill_by_value."""

    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
        axes = ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[-2, 2])

        surface = Surface(
            lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(16, 16),
            checkerboard_colors=False,
        )
        surface.set_fill_by_value(
            axes=axes,
            colorscale=[(BLUE, -1), (GREEN, 0), (RED, 1)],
            axis=2,  # color by z
        )
        self.add(axes, surface)


class PlotSurfaceMethod(ThreeDScene):
    """
    axes.plot_surface(
        function,              # (u, v) -> z
        u_range=None,          # (u_min, u_max)
        v_range=None,          # (v_min, v_max)
        colorscale=None,       # list of colors or (color, pivot) tuples
        colorscale_axis=2,     # 0=x, 1=y, 2=z
        resolution=(32, 32),   # via Surface kwargs
    )
    """

    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-60 * DEGREES)
        axes = ThreeDAxes(x_range=(-3, 3), y_range=(-3, 3), z_range=(-5, 5))

        surface = axes.plot_surface(
            lambda u, v: 2 * np.sin(u) + 2 * np.cos(v),
            u_range=(-3, 3),
            v_range=(-3, 3),
            colorscale=[BLUE, GREEN, YELLOW, ORANGE, RED],
            colorscale_axis=2,
            resolution=(16, 16),
        )
        self.add(axes, surface)


class ThreeDParametricSurface(ThreeDScene):
    """Parametric surfaces: sphere, torus, Klein bottle."""

    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES)
        axes = ThreeDAxes()

        # --- Sphere ---
        sphere = Surface(
            lambda u, v: axes.c2p(
                np.cos(u) * np.cos(v),
                np.cos(u) * np.sin(v),
                np.sin(u),
            ),
            u_range=[-PI / 2, PI / 2],
            v_range=[0, TAU],
            resolution=(16, 32),
            checkerboard_colors=[BLUE_D, BLUE_E],
        )
        self.add(axes, sphere)


class ThreeDParametricCurve(ThreeDScene):
    """3D parametric curve: helix."""

    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=-45 * DEGREES)
        axes = ThreeDAxes()

        helix = ParametricFunction(
            lambda t: axes.c2p(
                np.cos(t),
                np.sin(t),
                t * 0.2,
            ),
            t_range=[-4 * PI, 4 * PI, 0.01],
            color=YELLOW,
            stroke_width=3,
        )
        self.add(axes, helix)


# =============================================================================
# 14. STATISTICAL PLOTS — histograms, box plots, scatter
# =============================================================================
# NOTE: Manim CE does NOT have built-in Histogram, BoxPlot, or ScatterPlot
# classes. These must be built from primitives.

class HistogramFromBars(Scene):
    """Building a histogram using BarChart with adjacent bars."""

    def construct(self):
        # Simulate histogram data: frequency counts for bins
        np.random.seed(42)
        data = np.random.normal(50, 15, 500)
        bin_edges = np.arange(0, 101, 10)
        counts, _ = np.histogram(data, bins=bin_edges)

        chart = BarChart(
            values=counts.tolist(),
            bar_names=[f"{e}" for e in bin_edges[:-1]],
            y_range=[0, max(counts) + 10, 20],
            x_length=10,
            y_length=5,
            bar_width=0.95,  # nearly touching = histogram style
            bar_colors=[BLUE, TEAL],
            bar_fill_opacity=0.7,
            bar_stroke_width=1,
            x_axis_config={"font_size": 18},
        )
        labels = chart.get_bar_labels(font_size=16)
        self.add(chart, labels)


class ScatterPlotFromDots(Scene):
    """Building a scatter plot using Dots on Axes."""

    def construct(self):
        ax = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 10, 1],
            x_length=8,
            y_length=6,
            axis_config={"include_numbers": True, "font_size": 20},
        )
        self.add(ax)

        # Generate scatter data
        np.random.seed(42)
        n = 50
        x_data = np.random.uniform(1, 9, n)
        y_data = 0.8 * x_data + np.random.normal(0, 1, n)

        dots = VGroup(*[
            Dot(ax.c2p(x, y), color=BLUE, radius=0.04, fill_opacity=0.7)
            for x, y in zip(x_data, y_data)
        ])
        self.add(dots)

        # Add regression line
        slope = np.polyfit(x_data, y_data, 1)
        reg_line = ax.plot(
            lambda x: slope[0] * x + slope[1],
            x_range=[0.5, 9.5],
            color=RED,
            stroke_width=2,
        )
        self.add(reg_line)


class BoxPlotFromPrimitives(Scene):
    """Building a box plot from rectangles and lines."""

    def construct(self):
        ax = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 100, 10],
            x_length=8,
            y_length=6,
            axis_config={"include_numbers": True, "font_size": 18},
        )
        self.add(ax)

        # Data for three groups
        datasets = [
            {"q1": 25, "median": 50, "q3": 75, "whisker_low": 10, "whisker_high": 90},
            {"q1": 35, "median": 55, "q3": 70, "whisker_low": 20, "whisker_high": 85},
            {"q1": 40, "median": 60, "q3": 80, "whisker_low": 15, "whisker_high": 95},
        ]

        box_width = 0.3
        for i, d in enumerate(datasets):
            x_pos = i + 1

            # Box (Q1 to Q3)
            box = Rectangle(
                width=box_width * ax.get_x_unit_size(),
                height=abs(ax.c2p(0, d["q3"])[1] - ax.c2p(0, d["q1"])[1]),
                fill_color=BLUE,
                fill_opacity=0.5,
                stroke_color=WHITE,
                stroke_width=2,
            )
            box_center_y = (ax.c2p(0, d["q1"])[1] + ax.c2p(0, d["q3"])[1]) / 2
            box.move_to([ax.c2p(x_pos, 0)[0], box_center_y, 0])
            self.add(box)

            # Median line
            median_line = Line(
                ax.c2p(x_pos - box_width / 2, d["median"]),
                ax.c2p(x_pos + box_width / 2, d["median"]),
                color=RED,
                stroke_width=3,
            )
            self.add(median_line)

            # Whiskers
            whisker_low = Line(
                ax.c2p(x_pos, d["whisker_low"]),
                ax.c2p(x_pos, d["q1"]),
                color=WHITE,
                stroke_width=1.5,
            )
            whisker_high = Line(
                ax.c2p(x_pos, d["q3"]),
                ax.c2p(x_pos, d["whisker_high"]),
                color=WHITE,
                stroke_width=1.5,
            )
            # Whisker caps
            cap_low = Line(
                ax.c2p(x_pos - box_width / 4, d["whisker_low"]),
                ax.c2p(x_pos + box_width / 4, d["whisker_low"]),
                color=WHITE,
            )
            cap_high = Line(
                ax.c2p(x_pos - box_width / 4, d["whisker_high"]),
                ax.c2p(x_pos + box_width / 4, d["whisker_high"]),
                color=WHITE,
            )
            self.add(whisker_low, whisker_high, cap_low, cap_high)


# =============================================================================
# 15. ANIMATED DATA CHANGES — morphing between datasets
# =============================================================================

class MorphingBetweenGraphs(Scene):
    """Transform one graph into another."""

    def construct(self):
        ax = Axes(x_range=[-4, 4, 1], y_range=[-2, 2, 0.5], x_length=10, y_length=5)
        self.add(ax)

        g1 = ax.plot(lambda x: np.sin(x), color=BLUE)
        g2 = ax.plot(lambda x: np.cos(x), color=RED)
        g3 = ax.plot(lambda x: 0.5 * np.sin(2 * x), color=GREEN)

        self.play(Create(g1))
        self.wait(0.5)
        self.play(Transform(g1, g2), run_time=2)
        self.wait(0.5)
        self.play(Transform(g1, g3), run_time=2)
        self.wait(0.5)


class MorphingBarCharts(Scene):
    """Animate bar chart value changes smoothly."""

    def construct(self):
        chart = BarChart(
            values=[20, 40, 60, 80, 100],
            bar_names=["A", "B", "C", "D", "E"],
            y_range=[0, 100, 20],
            bar_colors=[BLUE, GREEN, YELLOW, ORANGE, RED],
        )
        self.play(Create(chart))
        self.wait(0.5)

        # Morph via become
        datasets = [
            [100, 80, 60, 40, 20],   # reverse
            [50, 50, 50, 50, 50],    # all equal
            [10, 90, 30, 70, 50],    # random
            [20, 40, 60, 80, 100],   # back to original
        ]

        for data in datasets:
            new_chart = chart.copy()
            new_chart.change_bar_values(data)
            self.play(chart.animate.become(new_chart), run_time=1.5)
            self.wait(0.3)


class MorphingLineGraphs(Scene):
    """Morphing between line graphs (discrete data)."""

    def construct(self):
        ax = Axes(
            x_range=[0, 6, 1],
            y_range=[0, 10, 1],
            axis_config={"include_numbers": True},
        )
        self.add(ax)

        x_vals = [0, 1, 2, 3, 4, 5]

        dataset_1 = [2, 5, 3, 8, 4, 7]
        dataset_2 = [7, 3, 8, 2, 9, 1]

        lg1 = ax.plot_line_graph(x_vals, dataset_1, line_color=BLUE)
        self.play(Create(lg1["line_graph"]), FadeIn(lg1["vertex_dots"]))
        self.wait(0.5)

        lg2 = ax.plot_line_graph(x_vals, dataset_2, line_color=RED)
        self.play(
            Transform(lg1["line_graph"], lg2["line_graph"]),
            Transform(lg1["vertex_dots"], lg2["vertex_dots"]),
            run_time=2,
        )
        self.wait(1)


class AnimatedScatterPlot(Scene):
    """Dots moving from one distribution to another."""

    def construct(self):
        ax = Axes(x_range=[-5, 5, 1], y_range=[-5, 5, 1])
        self.add(ax)

        np.random.seed(42)
        n = 30

        # Initial positions: cluster at (-2, -2)
        x1 = np.random.normal(-2, 0.5, n)
        y1 = np.random.normal(-2, 0.5, n)

        # Target positions: cluster at (2, 2)
        x2 = np.random.normal(2, 0.5, n)
        y2 = np.random.normal(2, 0.5, n)

        dots = VGroup(*[
            Dot(ax.c2p(x, y), color=BLUE, radius=0.05)
            for x, y in zip(x1, y1)
        ])
        self.play(FadeIn(dots))
        self.wait(0.5)

        # Animate each dot to new position
        anims = [
            dot.animate.move_to(ax.c2p(nx, ny))
            for dot, nx, ny in zip(dots, x2, y2)
        ]
        self.play(*anims, run_time=3)
        self.wait(1)


# =============================================================================
# 16. SCALE CLASSES — LinearBase, LogBase
# =============================================================================

class LogScaleAxes(Scene):
    """
    LogBase(base=10, custom_labels=True)
        function(value)          -> base^value
        inverse_function(value)  -> log_base(value)
        get_custom_labels(val_range) -> labels like 10^2

    LinearBase(scale_factor=1.0)
        function(value)          -> scale_factor * value
        inverse_function(value)  -> value / scale_factor

    Usage: pass to axis_config or directly to Axes y_axis_config.
    """

    def construct(self):
        # Logarithmic y-axis
        ax = Axes(
            x_range=[0, 10, 1],
            y_range=[-1, 5, 1],  # these are exponents: 10^-1 to 10^5
            x_length=10,
            y_length=5,
            tips=False,
            axis_config={"include_numbers": True, "font_size": 20},
            y_axis_config={"scaling": LogBase(base=10, custom_labels=True)},
        )
        self.add(ax)

        # Plot exponential growth: y = 2^x appears linear on log scale
        graph = ax.plot(
            lambda x: 2 ** x,
            x_range=[0, 10],
            use_smoothing=False,
            color=BLUE,
        )
        self.add(graph)


class LogLogAxes(Scene):
    """Both axes logarithmic."""

    def construct(self):
        ax = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 1],
            x_length=8,
            y_length=5,
            tips=False,
            x_axis_config={"scaling": LogBase(base=10, custom_labels=True)},
            y_axis_config={"scaling": LogBase(base=10, custom_labels=True)},
        )
        self.add(ax)

        # Power law: y = x^2 => log y = 2 * log x (straight line)
        graph = ax.plot(
            lambda x: x ** 2,
            x_range=[1, 10000],
            use_smoothing=False,
            color=GREEN,
        )
        self.add(graph)


# =============================================================================
# BONUS: COMPLETE WORKFLOW SCENES
# =============================================================================

class CompleteDerivativeVisualization(Scene):
    """Full calculus visualization: function, tangent, derivative, area."""

    def construct(self):
        ax = Axes(
            x_range=[-1, 5, 1],
            y_range=[-1, 10, 2],
            x_length=10,
            y_length=5,
            tips=True,
        ).add_coordinates()
        self.play(Create(ax), run_time=1)

        # Plot f(x) = x^2
        f = ax.plot(lambda x: x ** 2, color=BLUE, x_range=[0, 3])
        f_label = ax.get_graph_label(f, "x^2", x_val=2.5, direction=UL)
        self.play(Create(f), Write(f_label))

        # Animated tangent
        x_tracker = ValueTracker(0.5)

        tangent = always_redraw(
            lambda: ax.get_secant_slope_group(
                x=x_tracker.get_value(),
                graph=f,
                dx=0.01,
                secant_line_color=YELLOW,
                secant_line_length=3,
            )
        )
        dot = always_redraw(
            lambda: Dot(ax.i2gp(x_tracker.get_value(), f), color=RED)
        )
        self.add(tangent, dot)
        self.play(x_tracker.animate.set_value(2.5), run_time=3)

        # Show derivative
        f_prime = ax.plot_derivative_graph(f, color=GREEN)
        fp_label = ax.get_graph_label(f_prime, "2x", x_val=2, direction=RIGHT)
        self.play(Create(f_prime), Write(fp_label))

        # Animated area
        area_upper = ValueTracker(0.1)
        area = always_redraw(
            lambda: ax.get_area(
                f,
                x_range=[0, max(0.01, area_upper.get_value())],
                color=(BLUE, GREEN),
                opacity=0.3,
            )
        )
        self.add(area)
        self.play(area_upper.animate.set_value(3), run_time=3, rate_func=linear)
        self.wait(1)


class CompletePolarVisualization(Scene):
    """Animated polar curve tracing with dynamic equation."""

    def construct(self):
        plane = PolarPlane(
            radius_max=3,
            size=5,
            azimuth_units="PI radians",
        ).add_coordinates()
        self.play(Create(plane), run_time=1)

        n_petals = ValueTracker(2)
        t_upper = ValueTracker(0.01)

        curve = always_redraw(
            lambda: plane.plot_polar_graph(
                lambda theta: 2 * np.sin(n_petals.get_value() * theta),
                theta_range=[0, t_upper.get_value()],
                color=ORANGE,
                stroke_width=3,
            )
        )

        petal_label = always_redraw(
            lambda: MathTex(
                rf"r = 2\sin({int(n_petals.get_value())}\theta)",
                font_size=28, color=ORANGE,
            ).to_corner(UR)
        )

        self.add(curve, petal_label)
        self.play(t_upper.animate.set_value(2 * PI), run_time=4, rate_func=linear)
        self.wait(0.5)

        # Change number of petals
        self.play(n_petals.animate.set_value(5), t_upper.animate.set_value(0.01), run_time=0.5)
        self.play(t_upper.animate.set_value(2 * PI), run_time=4, rate_func=linear)


class Complete3DVisualization(ThreeDScene):
    """Full 3D surface with camera rotation and color by value."""

    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-60 * DEGREES)

        axes = ThreeDAxes(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            z_range=(-2, 2, 0.5),
        )
        labels = axes.get_axis_labels()
        self.add(axes, labels)

        # Surface: z = sin(sqrt(x^2 + y^2))
        surface = Surface(
            lambda u, v: axes.c2p(
                u, v,
                np.sin(np.sqrt(u ** 2 + v ** 2 + 0.01))
            ),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(24, 24),
            checkerboard_colors=False,
            fill_opacity=0.8,
        )
        surface.set_fill_by_value(
            axes=axes,
            colorscale=[(BLUE, -1), (GREEN, 0), (YELLOW, 0.5), (RED, 1)],
            axis=2,
        )
        self.play(Create(surface), run_time=2)

        # Rotate camera
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)
        self.stop_ambient_camera_rotation()


# =============================================================================
# PATTERN INDEX — for script_generator.py
# =============================================================================

PLOT_REFERENCE_INDEX = {
    "numberline": {
        "classes": [
            "NumberLineEveryParameter",
            "NumberLineCustomLabels",
            "NumberLineLogarithmic",
            "UnitIntervalExample",
        ],
        "keywords": ["number line", "tick", "scale", "logarithmic"],
    },
    "axes": {
        "classes": [
            "AxesEveryParameter",
            "AxesAllMethods",
            "AxesPlotEveryParameter",
            "PlotLineGraphEveryParameter",
            "GetAreaEveryParameter",
            "GetRiemannRectanglesEveryParameter",
            "GetSecantSlopeGroupEveryParameter",
            "GetTLabelEveryParameter",
            "CalculusMethods",
            "GetVerticalLinesToGraphExample",
            "PlotImplicitCurveExample",
        ],
        "keywords": ["axes", "plot", "graph", "area", "riemann", "secant", "tangent",
                      "derivative", "integral", "T-label", "implicit"],
    },
    "numberplane": {
        "classes": ["NumberPlaneEveryParameter", "NumberPlaneNonlinearTransform"],
        "keywords": ["grid", "plane", "transform", "nonlinear"],
    },
    "polarplane": {
        "classes": ["PolarPlaneEveryParameter", "PolarPlaneGraphing"],
        "keywords": ["polar", "azimuth", "radius", "rose", "cardioid"],
    },
    "complexplane": {
        "classes": ["ComplexPlaneEveryMethod", "ComplexPlaneAnimated"],
        "keywords": ["complex", "imaginary", "real", "complex multiplication"],
    },
    "threedaxes": {
        "classes": ["ThreeDAxesEveryParameter"],
        "keywords": ["3d", "three", "z-axis"],
    },
    "parametric": {
        "classes": [
            "ParametricFunctionEveryParameter",
            "FunctionGraphEveryParameter",
            "ImplicitFunctionEveryParameter",
            "ParametricCurvePatterns",
            "AnimatedParametricCurve",
            "PlotParametricCurveExample",
        ],
        "keywords": ["parametric", "lissajous", "spiral", "butterfly", "epicycloid"],
    },
    "valuetracker": {
        "classes": [
            "ValueTrackerReference",
            "MovingDotAlongCurve",
            "GrowingShrinkingArea",
            "AnimatedTangentLine",
            "DynamicFunctionPlotting",
            "AnimatedRiemannSum",
        ],
        "keywords": ["animate", "tracker", "dynamic", "moving", "growing", "interactive"],
    },
    "barchart": {
        "classes": [
            "BarChartEveryParameter",
            "BarChartAnimations",
            "BarChartWithChangeBarValues",
        ],
        "keywords": ["bar", "chart", "histogram", "comparison"],
    },
    "multiple_plots": {
        "classes": ["MultiplePlotsOnSameAxes", "MultiplePlotsWithColorscale"],
        "keywords": ["overlay", "multiple", "legend", "colorscale"],
    },
    "surface_3d": {
        "classes": [
            "SurfaceEveryParameter",
            "SurfaceColorByValue",
            "PlotSurfaceMethod",
            "ThreeDParametricSurface",
            "ThreeDParametricCurve",
        ],
        "keywords": ["surface", "3d", "mesh", "sphere", "torus", "helix"],
    },
    "statistical": {
        "classes": [
            "HistogramFromBars",
            "ScatterPlotFromDots",
            "BoxPlotFromPrimitives",
        ],
        "keywords": ["histogram", "scatter", "box plot", "statistics", "regression"],
    },
    "morphing": {
        "classes": [
            "MorphingBetweenGraphs",
            "MorphingBarCharts",
            "MorphingLineGraphs",
            "AnimatedScatterPlot",
        ],
        "keywords": ["morph", "transform", "transition", "animate data"],
    },
    "scales": {
        "classes": ["LogScaleAxes", "LogLogAxes"],
        "keywords": ["logarithmic", "log scale", "log-log", "exponential"],
    },
    "complete_workflows": {
        "classes": [
            "CompleteDerivativeVisualization",
            "CompletePolarVisualization",
            "Complete3DVisualization",
        ],
        "keywords": ["full", "complete", "calculus", "polar animation", "3d rotation"],
    },
}
