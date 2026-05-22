"""
Comprehensive Manim Community Edition Bugs, Errors & Pitfalls Reference
========================================================================

This file documents every known Manim CE pitfall that can crash or degrade
AI-generated scripts, along with the regex/AST fix for each one.

Used to build a robust sanitize_script() function.

Organized by category:
  1. RENDERING ERRORS (crash the subprocess)
  2. API DIFFERENCES (manimgl vs Manim CE)
  3. ANIMATION MISTAKES (wrong behavior, not crash)
  4. TEXT / LATEX ISSUES
  5. PERFORMANCE ISSUES
  6. OBJECT LIFECYCLE / CLEANUP BUGS
  7. COORDINATE / POSITIONING BUGS
  8. COLOR / STYLING BUGS
  9. IMPORT / MODULE ISSUES
"""

import re

# =============================================================================
# CATEGORY 1: RENDERING ERRORS (crash the manim subprocess)
# =============================================================================

RENDERING_ERRORS = [

    # ── 1.1  float NaN in point arrays ──────────────────────────────────────
    {
        "id": "nan_in_points",
        "symptom": "ValueError: cannot convert float NaN to integer",
        "also_seen_as": "RuntimeError: Point coordinates contain NaN values",
        "root_cause": (
            "Division by zero or log(0) in a lambda passed to axes.plot(). "
            "Manim tries to sample the function at domain points that produce "
            "NaN/Inf, and the resulting bezier points crash the renderer."
        ),
        "example_bad": """axes.plot(lambda x: 1/x, x_range=[-3, 3])""",
        "fix": (
            "Clamp the function domain or use np.where / np.clip to avoid "
            "singularities. Alternatively, split into two plot segments."
        ),
        "example_good": """
# Option 1: Restrict domain to avoid singularity
axes.plot(lambda x: 1/x, x_range=[0.1, 3])

# Option 2: Use np.where to handle singularity
axes.plot(lambda x: np.where(np.abs(x) < 0.01, 0, 1/x), x_range=[-3, 3])
""",
        "regex_fix": None,  # Needs AST analysis; can't reliably regex-fix
        "sanitize_priority": "HIGH",
    },

    # ── 1.2  Empty VGroup in animation ──────────────────────────────────────
    {
        "id": "empty_vgroup_animation",
        "symptom": "IndexError: list index out of range (in animation internals)",
        "also_seen_as": "ValueError: mobject has no points",
        "root_cause": (
            "Passing an empty VGroup() or a mobject with no submobjects to "
            "an animation like Write(), Create(), or FadeIn(). Write(VGroup()) "
            "crashes because it tries to iterate submobjects that don't exist."
        ),
        "example_bad": """
group = VGroup()  # empty
self.play(Write(group))
""",
        "fix": "Guard animations with an emptiness check, or ensure the group is populated.",
        "example_good": """
group = VGroup(*items) if items else None
if group:
    self.play(Write(group))
""",
        "regex_fix": None,
        "sanitize_priority": "MEDIUM",
    },

    # ── 1.3  max() in lambda (not vectorized) ──────────────────────────────
    {
        "id": "max_in_lambda",
        "symptom": "TypeError: '>' not supported between instances of 'numpy.ndarray' and 'int'",
        "also_seen_as": "ValueError: The truth value of an array is ambiguous",
        "root_cause": (
            "Python's built-in max() doesn't work on numpy arrays. When "
            "axes.plot() passes an array of x values to the lambda, max(0, x) "
            "fails because numpy array comparison doesn't return a single bool."
        ),
        "example_bad": """axes.plot(lambda x: max(0, x))""",
        "fix": "Use np.maximum() which is element-wise.",
        "example_good": """axes.plot(lambda x: np.maximum(0, x))""",
        "regex_fix": r"""re.sub(r'lambda\s+(\w+)\s*:\s*max\(', r'lambda \1: np.maximum(', code)""",
        "sanitize_priority": "CRITICAL",
    },

    # ── 1.4  min() in lambda (same issue) ──────────────────────────────────
    {
        "id": "min_in_lambda",
        "symptom": "TypeError: '>' not supported between instances of 'numpy.ndarray' and 'int'",
        "root_cause": "Same as max() — Python min() isn't vectorized.",
        "example_bad": """axes.plot(lambda x: min(1, x))""",
        "fix": "Use np.minimum().",
        "example_good": """axes.plot(lambda x: np.minimum(1, x))""",
        "regex_fix": r"""re.sub(r'lambda\s+(\w+)\s*:\s*min\(', r'lambda \1: np.minimum(', code)""",
        "sanitize_priority": "CRITICAL",
    },

    # ── 1.5  abs() in lambda (not vectorized) ──────────────────────────────
    {
        "id": "abs_in_lambda",
        "symptom": "TypeError or incorrect behavior with numpy arrays",
        "root_cause": "Python abs() works on arrays but np.abs() is safer and consistent.",
        "example_bad": """axes.plot(lambda x: abs(x))""",
        "fix": "Use np.abs().",
        "example_good": """axes.plot(lambda x: np.abs(x))""",
        "regex_fix": r"""re.sub(r'lambda\s+(\w+)\s*:(.*)(?<!\w)abs\(', r'lambda \1:\2np.abs(', code)""",
        "sanitize_priority": "LOW",
    },

    # ── 1.6  ShowCreation (manimgl name, not in CE) ────────────────────────
    {
        "id": "show_creation",
        "symptom": "NameError: name 'ShowCreation' is not defined",
        "root_cause": (
            "ShowCreation is from manimgl (3b1b's version). "
            "Manim CE renamed it to Create."
        ),
        "example_bad": """self.play(ShowCreation(circle))""",
        "fix": "Use Create() instead.",
        "example_good": """self.play(Create(circle))""",
        "regex_fix": r"""re.sub(r'\bShowCreation\b', 'Create', code)""",
        "sanitize_priority": "CRITICAL",
    },

    # ── 1.7  get_graph() (old API) ─────────────────────────────────────────
    {
        "id": "get_graph",
        "symptom": "AttributeError: 'Axes' object has no attribute 'get_graph'",
        "root_cause": (
            "get_graph() was the manimgl method. Manim CE uses axes.plot()."
        ),
        "example_bad": """graph = axes.get_graph(lambda x: x**2)""",
        "fix": "Use axes.plot().",
        "example_good": """graph = axes.plot(lambda x: x**2)""",
        "regex_fix": r"""re.sub(r'\.get_graph\(', '.plot(', code)""",
        "sanitize_priority": "CRITICAL",
    },

    # ── 1.8  get_graph_label() (deprecated name) ───────────────────────────
    {
        "id": "get_graph_label_deprecated",
        "symptom": "AttributeError or DeprecationWarning for get_graph_label",
        "root_cause": "In some CE versions, get_graph_label was renamed/restructured.",
        "example_bad": """label = axes.get_graph_label(graph, label='f(x)')""",
        "fix": "Use axes.get_graph_label() with MathTex, or manually position a label.",
        "example_good": """
label = MathTex("f(x)").next_to(graph, UR)
""",
        "regex_fix": None,
        "sanitize_priority": "LOW",
    },

    # ── 1.9  TexMobject / TextMobject (removed in CE) ─────────────────────
    {
        "id": "tex_mobject_old",
        "symptom": "NameError: name 'TexMobject' / 'TextMobject' is not defined",
        "root_cause": (
            "TexMobject and TextMobject were manimgl names. "
            "Manim CE uses MathTex and Text."
        ),
        "example_bad": """eq = TexMobject(r'E=mc^2')""",
        "fix": "Use MathTex or Tex.",
        "example_good": """eq = MathTex(r'E=mc^2')""",
        "regex_fix": r"""
re.sub(r'\bTexMobject\b', 'MathTex', code)
re.sub(r'\bTextMobject\b', 'Text', code)
""",
        "sanitize_priority": "CRITICAL",
    },

    # ── 1.10  move_camera / set_camera_orientation on 2D Scene ─────────────
    {
        "id": "move_camera_2d",
        "symptom": "AttributeError: 'Camera' object has no attribute 'frame' / 'phi'",
        "root_cause": (
            "move_camera() and set_camera_orientation() only exist on "
            "ThreeDScene. Using them on a regular Scene or VoiceoverScene crashes."
        ),
        "example_bad": """
class MyScene(Scene):
    def construct(self):
        self.move_camera(phi=60*DEGREES)
""",
        "fix": "Remove camera manipulation for 2D scenes, or use ThreeDScene.",
        "example_good": """# Removed — 2D scene doesn't support camera movement""",
        "regex_fix": r"""
re.sub(r'^\s*self\.move_camera\(.*?\)\s*$', '', code, flags=re.MULTILINE)
re.sub(r'^\s*self\.set_camera_orientation\(.*?\)\s*$', '', code, flags=re.MULTILINE)
""",
        "sanitize_priority": "HIGH",
    },

    # ── 1.11  Surface / ThreeDAxes on 2D Scene ────────────────────────────
    {
        "id": "3d_objects_on_2d_scene",
        "symptom": "Various errors about missing z-axis or 3D rendering",
        "root_cause": (
            "Surface, ThreeDAxes, and ParametricSurface require ThreeDScene. "
            "Using them with a plain Scene produces rendering artifacts or crashes."
        ),
        "example_bad": """
class MyScene(Scene):
    def construct(self):
        axes = ThreeDAxes()
""",
        "fix": "Use Axes (2D) instead of ThreeDAxes for 2D scenes.",
        "example_good": """
class MyScene(Scene):
    def construct(self):
        axes = Axes(x_range=[-3,3], y_range=[-3,3])
""",
        "regex_fix": r"""re.sub(r'\bThreeDAxes\b', 'Axes', code)""",
        "sanitize_priority": "HIGH",
    },

    # ── 1.12  Negative or zero run_time ────────────────────────────────────
    {
        "id": "negative_run_time",
        "symptom": "ValueError: run_time must be positive",
        "also_seen_as": "ZeroDivisionError in animation interpolation",
        "root_cause": (
            "Computed run_time from tracker.get_remaining_duration() can be "
            "negative or zero. Passing run_time=0 or run_time=-1 to self.play() "
            "crashes the animation system."
        ),
        "example_bad": """
remaining = tracker.get_remaining_duration()
self.play(FadeOut(obj), run_time=remaining)  # remaining could be <= 0
""",
        "fix": "Always clamp run_time to a positive minimum.",
        "example_good": """
remaining = tracker.get_remaining_duration(buff=-0.3)
if remaining > 0:
    self.wait(remaining)
""",
        "regex_fix": None,  # Pattern is already correct in templates
        "sanitize_priority": "MEDIUM",
    },

    # ── 1.13  self.wait() with negative or zero duration ──────────────────
    {
        "id": "negative_wait",
        "symptom": "ValueError: Duration must be positive",
        "root_cause": "self.wait(0) or self.wait(-1) is invalid in Manim CE.",
        "example_bad": """self.wait(remaining)  # remaining could be <= 0""",
        "fix": "Guard with if > 0.",
        "example_good": """
if remaining > 0:
    self.wait(remaining)
""",
        "regex_fix": None,
        "sanitize_priority": "MEDIUM",
    },

    # ── 1.14  LaTeX compilation failure ────────────────────────────────────
    {
        "id": "latex_compilation_error",
        "symptom": "RuntimeError: LaTeX compilation error / dvi file not found",
        "root_cause": (
            "Invalid LaTeX in MathTex strings. Common culprits: "
            "unescaped underscores, unmatched braces, \\text{} without amsmath, "
            "using $ signs inside MathTex (already in math mode)."
        ),
        "example_bad": r"""
MathTex(r'E = mc^{2')  # missing closing brace
MathTex(r'$x^2$')       # $ signs not needed — already in math mode
MathTex(r'hello_world')  # unescaped underscore
""",
        "fix": "Validate LaTeX syntax. Remove $ from MathTex. Escape underscores.",
        "example_good": r"""
MathTex(r'E = mc^{2}')
MathTex(r'x^2')
MathTex(r'hello\_world')
""",
        "regex_fix": r"""
# Remove $ signs from MathTex content
re.sub(r'MathTex\(r?["\'](\$)(.*?)(\$)["\']\)', fix_mathtex_dollars, code)
""",
        "sanitize_priority": "HIGH",
    },

    # ── 1.15  Text() with invalid/unavailable font ────────────────────────
    {
        "id": "missing_font",
        "symptom": "WARNING: Font family 'XYZ' not found, using default",
        "root_cause": (
            "Text() uses Pango for rendering. If the specified font isn't "
            "installed, it silently falls back but can produce misaligned text."
        ),
        "example_bad": """Text("Hello", font="Fira Code")  # may not be installed""",
        "fix": "Don't specify custom fonts unless certain they exist. Remove font= param.",
        "example_good": """Text("Hello")  # uses system default""",
        "regex_fix": r"""re.sub(r',\s*font\s*=\s*["\'][^"\']*["\']', '', code)""",
        "sanitize_priority": "LOW",
    },

    # ── 1.16  Trying to animate a removed mobject ──────────────────────────
    {
        "id": "animate_removed_mobject",
        "symptom": "ValueError: Mobject is not in the Scene",
        "root_cause": (
            "Calling self.play(FadeOut(obj)) when obj was already removed, "
            "or trying to animate an object that was never added to the scene."
        ),
        "example_bad": """
self.play(FadeOut(circle))
self.play(FadeOut(circle))  # already removed!
""",
        "fix": "Track what's on screen. Don't double-remove.",
        "example_good": """
self.play(FadeOut(circle))
# circle is now removed; don't animate it again
""",
        "regex_fix": None,
        "sanitize_priority": "MEDIUM",
    },

    # ── 1.17  SyntaxError from raw f-string with backslashes ──────────────
    {
        "id": "fstring_backslash",
        "symptom": "SyntaxError: f-string expression part cannot include a backslash",
        "root_cause": (
            "In Python, f-strings cannot contain backslashes inside the {} "
            "expression part. Claude sometimes generates f-strings with \\n "
            "or LaTeX backslashes inside the braces."
        ),
        "example_bad": r"""f"x = {val:.2f}\n"  # OK in string part, but...""",
        "fix": "Move backslash expressions outside the f-string braces.",
        "example_good": r"""f"x = {val:.2f}" + "\n" """,
        "regex_fix": None,  # Hard to regex; caught by compile() check
        "sanitize_priority": "LOW",
    },

    # ── 1.18  Division by zero in axes range ───────────────────────────────
    {
        "id": "axes_zero_range",
        "symptom": "ZeroDivisionError in coordinate_systems.py",
        "root_cause": (
            "x_range or y_range where min == max, e.g. x_range=[0, 0, 1]. "
            "Manim tries to compute scaling and divides by (max - min) = 0."
        ),
        "example_bad": """Axes(x_range=[0, 0, 1], y_range=[0, 1, 1])""",
        "fix": "Ensure ranges have non-zero span.",
        "example_good": """Axes(x_range=[-1, 1, 1], y_range=[0, 1, 1])""",
        "regex_fix": None,
        "sanitize_priority": "LOW",
    },

    # ── 1.19  Passing string color to ManimColor (hex without #) ──────────
    {
        "id": "color_missing_hash",
        "symptom": "ValueError: Invalid color string",
        "root_cause": "Hex colors must start with #. E.g. 'ff0000' is invalid, '#ff0000' is valid.",
        "example_bad": """Circle(color='ff0000')""",
        "fix": "Prepend # to hex colors.",
        "example_good": """Circle(color='#ff0000')""",
        "regex_fix": r"""re.sub(r"color=['\"]([0-9a-fA-F]{6})['\"]", r"color='#\1'", code)""",
        "sanitize_priority": "MEDIUM",
    },

    # ── 1.20  Transform between incompatible mobjects ──────────────────────
    {
        "id": "transform_incompatible",
        "symptom": "IndexError or visual glitches during Transform/ReplacementTransform",
        "root_cause": (
            "Transform/ReplacementTransform between mobjects with vastly different "
            "point counts can produce garbled visuals. TransformMatchingTex between "
            "non-MathTex objects crashes."
        ),
        "example_bad": """
text = Text("Hello")
circle = Circle()
self.play(TransformMatchingTex(text, circle))  # text isn't MathTex!
""",
        "fix": "Use ReplacementTransform for generic transforms. TransformMatchingTex only for MathTex.",
        "example_good": """
text = Text("Hello")
circle = Circle()
self.play(ReplacementTransform(text, circle))
""",
        "regex_fix": None,
        "sanitize_priority": "MEDIUM",
    },

    # ── 1.21  Using math.* instead of np.* ────────────────────────────────
    {
        "id": "math_module_in_lambda",
        "symptom": "TypeError: only size-1 arrays can be converted to Python scalars",
        "root_cause": (
            "math.sin, math.cos, math.exp etc. don't work on numpy arrays. "
            "Manim passes array-typed x values to plot lambdas."
        ),
        "example_bad": """
import math
axes.plot(lambda x: math.sin(x))
""",
        "fix": "Use np.sin, np.cos, np.exp etc.",
        "example_good": """axes.plot(lambda x: np.sin(x))""",
        "regex_fix": r"""
re.sub(r'\bmath\.sin\b', 'np.sin', code)
re.sub(r'\bmath\.cos\b', 'np.cos', code)
re.sub(r'\bmath\.exp\b', 'np.exp', code)
re.sub(r'\bmath\.log\b', 'np.log', code)
re.sub(r'\bmath\.sqrt\b', 'np.sqrt', code)
re.sub(r'\bmath\.pi\b', 'np.pi', code)
re.sub(r'\bmath\.e\b', 'np.e', code)
re.sub(r'\bmath\.floor\b', 'np.floor', code)
re.sub(r'\bmath\.ceil\b', 'np.ceil', code)
re.sub(r'\bmath\.abs\b', 'np.abs', code)
re.sub(r'\bmath\.pow\b', 'np.power', code)
re.sub(r'\bmath\.fabs\b', 'np.abs', code)
re.sub(r'^import math\s*$', '', code, flags=re.MULTILINE)
""",
        "sanitize_priority": "HIGH",
    },

    # ── 1.22  Recursive / infinite updater ─────────────────────────────────
    {
        "id": "infinite_updater",
        "symptom": "RecursionError: maximum recursion depth exceeded / Render hangs forever",
        "root_cause": (
            "An always_redraw() or add_updater() that modifies the object it's "
            "attached to in a way that triggers another update, creating infinite recursion."
        ),
        "example_bad": """
def bad_updater(mob):
    mob.shift(UP * 0.01)  # triggers redraw, which calls updater again
    mob.become(Circle())  # become can trigger recursive updates
""",
        "fix": "Updaters should only SET properties, not trigger new animations or becomes.",
        "example_good": """
x = ValueTracker(0)
dot = always_redraw(lambda: Dot(axes.c2p(x.get_value(), 0)))
""",
        "regex_fix": None,
        "sanitize_priority": "LOW",
    },
]


# =============================================================================
# CATEGORY 2: API DIFFERENCES (manimgl vs Manim CE)
# =============================================================================

API_DIFFERENCES = [

    # ── 2.1  ShowCreation → Create ─────────────────────────────────────────
    {
        "id": "manimgl_show_creation",
        "manimgl": "ShowCreation",
        "manim_ce": "Create",
        "regex_fix": r"""re.sub(r'\bShowCreation\b', 'Create', code)""",
    },

    # ── 2.2  get_graph → plot ──────────────────────────────────────────────
    {
        "id": "manimgl_get_graph",
        "manimgl": "axes.get_graph(func)",
        "manim_ce": "axes.plot(func)",
        "regex_fix": r"""re.sub(r'\.get_graph\(', '.plot(', code)""",
    },

    # ── 2.3  TexMobject → MathTex ─────────────────────────────────────────
    {
        "id": "manimgl_texmobject",
        "manimgl": "TexMobject(r'...')",
        "manim_ce": "MathTex(r'...')",
        "regex_fix": r"""re.sub(r'\bTexMobject\b', 'MathTex', code)""",
    },

    # ── 2.4  TextMobject → Text ───────────────────────────────────────────
    {
        "id": "manimgl_textmobject",
        "manimgl": "TextMobject('...')",
        "manim_ce": "Text('...')",
        "regex_fix": r"""re.sub(r'\bTextMobject\b', 'Text', code)""",
    },

    # ── 2.5  FadeInFromDown → FadeIn(shift=DOWN) ──────────────────────────
    {
        "id": "manimgl_fade_in_from",
        "manimgl": "FadeInFromDown(obj)",
        "manim_ce": "FadeIn(obj, shift=DOWN)",
        "regex_fix": r"""
re.sub(r'\bFadeInFromDown\b\(', 'FadeIn(shift=DOWN, ', code)  # approximate
re.sub(r'\bFadeInFrom\b', 'FadeIn', code)
re.sub(r'\bFadeOutAndShift\b', 'FadeOut', code)
""",
    },

    # ── 2.6  GrowFromCenter → GrowFromCenter (same in CE but needs import)──
    {
        "id": "manimgl_grow_from_center",
        "manimgl": "GrowFromCenter",
        "manim_ce": "GrowFromCenter (from manim.animation.growing)",
        "note": "Available in CE but sometimes not star-imported correctly.",
    },

    # ── 2.7  play_all → doesn't exist in CE ───────────────────────────────
    {
        "id": "manimgl_play_all",
        "manimgl": "self.play_all(...)",
        "manim_ce": "self.play(...)",
        "regex_fix": r"""re.sub(r'\bself\.play_all\b', 'self.play', code)""",
    },

    # ── 2.8  NumberPlane vs CoordinateSystem changes ───────────────────────
    {
        "id": "manimgl_numberplane",
        "manimgl": "NumberPlane(x_min=-5, x_max=5)",
        "manim_ce": "NumberPlane(x_range=[-5, 5, 1], y_range=[-5, 5, 1])",
        "note": "CE uses x_range/y_range, not x_min/x_max.",
    },

    # ── 2.9  ApplyMethod → .animate ───────────────────────────────────────
    {
        "id": "manimgl_apply_method",
        "manimgl": "ApplyMethod(obj.shift, UP)",
        "manim_ce": "obj.animate.shift(UP)",
        "regex_fix": None,  # Complex transform
        "note": "ApplyMethod still works in CE but .animate is preferred.",
    },

    # ── 2.10  self.camera.frame → self.camera (2D) ────────────────────────
    {
        "id": "manimgl_camera_frame",
        "manimgl": "self.camera.frame.animate.scale(0.5)",
        "manim_ce": "self.camera.frame_width = 7  # or use ScaleInPlace",
        "note": "Camera API is completely different between GL and CE.",
        "regex_fix": r"""
re.sub(r'self\.camera\.frame\.animate\.\w+\(.*?\)', '# Camera manipulation removed (CE)', code)
""",
    },

    # ── 2.11  CoordinateSystem.get_area → axes.get_area ───────────────────
    {
        "id": "manimgl_get_area",
        "note": "Available in CE as axes.get_area(graph, x_range, color, opacity).",
    },

    # ── 2.12  add_fixed_in_frame_mobjects → exists only in ThreeDScene ────
    {
        "id": "manimgl_fixed_in_frame",
        "manimgl": "self.add_fixed_in_frame_mobjects(label)",
        "manim_ce": "Only available in ThreeDScene. 2D scenes don't need it.",
        "regex_fix": r"""
re.sub(r'^\s*self\.add_fixed_in_frame_mobjects?\(.*?\)\s*$', '', code, flags=re.MULTILINE)
""",
    },

    # ── 2.13  set_color_by_gradient → set_color ───────────────────────────
    {
        "id": "manimgl_color_gradient",
        "manimgl": "obj.set_color_by_gradient(RED, BLUE)",
        "manim_ce": "obj.set_color(color=[RED, BLUE]) or obj.set_color_by_gradient(RED, BLUE)",
        "note": "set_color_by_gradient exists in CE, but syntax may differ.",
    },

    # ── 2.14  Animation.set_run_time → pass run_time= to constructor ──────
    {
        "id": "manimgl_set_run_time",
        "manimgl": "anim = Write(eq); anim.set_run_time(2)",
        "manim_ce": "self.play(Write(eq), run_time=2)",
    },

    # ── 2.15  Scene.embed() → doesn't exist in CE ─────────────────────────
    {
        "id": "manimgl_embed",
        "manimgl": "self.embed()  # opens interactive IPython",
        "manim_ce": "# No equivalent. Remove.",
        "regex_fix": r"""re.sub(r'^\s*self\.embed\(\)\s*$', '', code, flags=re.MULTILINE)""",
    },

    # ── 2.16  DecimalNumber.set_value → follow ValueTracker ───────────────
    {
        "id": "manimgl_decimal_set_value",
        "note": (
            "DecimalNumber in CE doesn't have set_value(). Use add_updater "
            "with a ValueTracker to update the displayed value."
        ),
    },
]


# =============================================================================
# CATEGORY 3: ANIMATION MISTAKES (wrong behavior, not always crash)
# =============================================================================

ANIMATION_MISTAKES = [

    # ── 3.1  Missing run_time → default 1s, too fast ──────────────────────
    {
        "id": "default_run_time",
        "symptom": "Animations feel rushed or jerky",
        "root_cause": "Default run_time is 1 second; Write() on complex objects needs 2-3s.",
        "fix": "Always specify run_time explicitly for Write and Create.",
    },

    # ── 3.2  Stale objects not cleaned up ──────────────────────────────────
    {
        "id": "stale_objects",
        "symptom": "Previous section's content still visible behind new content",
        "root_cause": "Forgot to FadeOut objects before building the next section.",
        "fix": "self.play(FadeOut(VGroup(...all_old_objects...))) before each new section.",
    },

    # ── 3.3  always_redraw with closure variable capture ───────────────────
    {
        "id": "closure_capture_in_redraw",
        "symptom": "All always_redraw lambdas use the same (last) variable value",
        "root_cause": (
            "Python closures capture variables by reference, not value. "
            "In a loop, all lambdas share the same loop variable."
        ),
        "example_bad": """
for i in range(5):
    dot = always_redraw(lambda: Dot(axes.c2p(i, 0)))  # all use i=4
""",
        "fix": "Use default argument to capture the value.",
        "example_good": """
for i in range(5):
    dot = always_redraw(lambda i=i: Dot(axes.c2p(i, 0)))
""",
    },

    # ── 3.4  Mixing .animate with regular methods ─────────────────────────
    {
        "id": "mixing_animate",
        "symptom": "Object jumps to final position instead of animating",
        "root_cause": (
            "Calling obj.shift(UP) (instant) when you meant "
            "obj.animate.shift(UP) (animated)."
        ),
        "example_bad": """
self.play(circle.shift(UP))  # instant shift, then nothing to animate
""",
        "fix": "Use .animate for animated transforms.",
        "example_good": """
self.play(circle.animate.shift(UP), run_time=1)
""",
    },

    # ── 3.5  Multiple simultaneous incompatible animations ─────────────────
    {
        "id": "conflicting_animations",
        "symptom": "Object teleports or produces visual artifacts",
        "root_cause": (
            "Playing two animations on the same mobject simultaneously "
            "(e.g., Transform + FadeOut on the same object)."
        ),
        "fix": "Sequence conflicting animations with separate self.play() calls.",
    },

    # ── 3.6  LaggedStartMap on empty group ─────────────────────────────────
    {
        "id": "laggedstart_empty",
        "symptom": "ZeroDivisionError or no animation plays",
        "root_cause": "LaggedStartMap(FadeIn, VGroup()) has no submobjects to iterate.",
        "fix": "Guard: only call if group has submobjects.",
    },

    # ── 3.7  rate_func=there_and_back on long animations ──────────────────
    {
        "id": "there_and_back_confusion",
        "symptom": "Object returns to start position unexpectedly",
        "root_cause": "there_and_back goes forward then reverses in the same run_time.",
        "fix": "Use linear or smooth for one-way animations.",
    },

    # ── 3.8  z_index issues: newer objects behind older ones ───────────────
    {
        "id": "z_index_ordering",
        "symptom": "Newly created objects hidden behind earlier ones",
        "root_cause": "Manim renders objects in add-order. Later adds are on top by default.",
        "fix": "Use obj.set_z_index(1) or self.bring_to_front(obj).",
    },

    # ── 3.9  Forgetting to add mobject before animating ────────────────────
    {
        "id": "forgot_to_add",
        "symptom": "Object appears only during animation, then vanishes",
        "root_cause": (
            "Using self.play(FadeIn(obj)) adds the object. But "
            "self.play(obj.animate.shift(UP)) requires the object already be in the scene."
        ),
        "fix": "Use self.add(obj) or FadeIn first.",
    },
]


# =============================================================================
# CATEGORY 4: TEXT / LATEX ISSUES
# =============================================================================

TEXT_LATEX_ISSUES = [

    # ── 4.1  MathTex with $ signs ──────────────────────────────────────────
    {
        "id": "mathtex_dollar_signs",
        "symptom": "LaTeX compilation error or doubled math mode",
        "root_cause": "MathTex already wraps content in $ $. Adding $ creates $$.",
        "example_bad": r"""MathTex(r'$x^2$')""",
        "fix": "Remove $ signs from MathTex strings.",
        "example_good": r"""MathTex(r'x^2')""",
        "regex_fix": r"""
# Strip $ from MathTex raw strings
re.sub(r"(MathTex\(r?['\"])\$(.+?)\$(['\"])", r'\1\2\3', code)
""",
        "sanitize_priority": "HIGH",
    },

    # ── 4.2  Unmatched braces in LaTeX ─────────────────────────────────────
    {
        "id": "unmatched_braces",
        "symptom": "RuntimeError: LaTeX compilation error",
        "root_cause": "Missing closing } in MathTex/Tex string.",
        "fix": "Count braces and ensure they match.",
        "regex_fix": None,  # Needs parser
        "sanitize_priority": "HIGH",
    },

    # ── 4.3  \\text{} in MathTex without amsmath ───────────────────────────
    {
        "id": "text_in_mathtex",
        "symptom": "LaTeX error: Undefined control sequence \\text",
        "root_cause": (
            "\\text{} requires amsmath package. Manim CE includes it by default "
            "but some installations may not. More commonly, nested \\text{} fails."
        ),
        "fix": "Use \\mathrm{} as a safer alternative, or Tex() for text-mode.",
        "example_good": r"""MathTex(r'\mathrm{ReLU}(x) = \max(0, x)')""",
    },

    # ── 4.4  Text too wide / overflows frame ───────────────────────────────
    {
        "id": "text_overflow",
        "symptom": "Text extends past the visible frame boundaries",
        "root_cause": (
            "Long strings with large font_size exceed the 14.22-unit frame width. "
            "Manim doesn't auto-wrap text."
        ),
        "fix": "Manually break text with \\n or reduce font_size. Use width parameter.",
        "example_good": """
Text("This is a very long line\\nthat we break into two", font_size=24)
# Or set a max width:
text = Text("Long text here", font_size=24)
if text.width > 12:
    text.scale_to_fit_width(12)
""",
    },

    # ── 4.5  MathTex with Python string formatting inside LaTeX ────────────
    {
        "id": "mathtex_fstring_latex",
        "symptom": "LaTeX error from misinterpreted format specifiers",
        "root_cause": (
            "Using f-strings with LaTeX: f'\\frac{{{x}}}{{{y}}}' is fragile. "
            "Braces get confused between Python and LaTeX."
        ),
        "fix": "Use raw strings with manual concatenation or .format().",
        "example_bad": r"""MathTex(f'x = {value:.2f}')""",
        "example_good": r"""MathTex(r'x = ' + f'{value:.2f}')""",
    },

    # ── 4.6  Using \\ for newline in MathTex ──────────────────────────────
    {
        "id": "mathtex_newline",
        "symptom": "LaTeX error or no line break appears",
        "root_cause": (
            "MathTex doesn't support \\\\. Use separate MathTex objects "
            "arranged with VGroup, or use Tex with \\\\."
        ),
        "fix": "Use VGroup of multiple MathTex for multi-line equations.",
        "example_good": """
eqs = VGroup(
    MathTex(r'f(x) = x^2'),
    MathTex(r'f\\'(x) = 2x'),
).arrange(DOWN)
""",
    },

    # ── 4.7  Unsupported LaTeX commands ────────────────────────────────────
    {
        "id": "unsupported_latex_commands",
        "symptom": "LaTeX compilation error: Undefined control sequence",
        "root_cause": (
            "Commands like \\mathbb, \\mathcal require amssymb or specific "
            "packages. Most are included by Manim's default template but some "
            "are not: \\bm, \\boldsymbol, \\cancel, \\xrightarrow."
        ),
        "fix": "Use Manim's tex_template to add required packages, or use alternatives.",
    },

    # ── 4.8  TransformMatchingTex with non-matching substrings ─────────────
    {
        "id": "transform_matching_tex_mismatch",
        "symptom": "Parts of equation appear/disappear instead of morphing",
        "root_cause": (
            "TransformMatchingTex matches by tex_string of each substring part. "
            "If the MathTex isn't split into matching substrings, it can't find "
            "correspondences and falls back to ugly FadeIn/FadeOut."
        ),
        "example_bad": r"""
eq1 = MathTex(r'a + b = c')  # one big string
eq2 = MathTex(r'c = a + b')  # one big string
self.play(TransformMatchingTex(eq1, eq2))  # nothing matches
""",
        "fix": "Split MathTex into matching substrings.",
        "example_good": r"""
eq1 = MathTex('a', '+', 'b', '=', 'c')
eq2 = MathTex('c', '=', 'a', '+', 'b')
self.play(TransformMatchingTex(eq1, eq2))  # each part matches
""",
    },
]


# =============================================================================
# CATEGORY 5: PERFORMANCE ISSUES
# =============================================================================

PERFORMANCE_ISSUES = [

    # ── 5.1  Too many plot points ──────────────────────────────────────────
    {
        "id": "too_many_plot_points",
        "symptom": "Render takes >10 minutes for a simple scene",
        "root_cause": (
            "axes.plot() with very fine x_range step (e.g., 0.001) creates "
            "thousands of bezier points. Combined with always_redraw(), this "
            "is recalculated every frame."
        ),
        "fix": "Use reasonable step sizes (0.1 or larger). For smooth curves, Manim interpolates.",
    },

    # ── 5.2  always_redraw with expensive computation ──────────────────────
    {
        "id": "expensive_always_redraw",
        "symptom": "Render hangs or takes >10 minutes",
        "root_cause": (
            "always_redraw() runs every single frame. If it creates complex "
            "objects (Axes, multiple plots, text), it's extremely slow."
        ),
        "fix": "Only redraw the minimum needed. Keep Axes static; only redraw the graph/dot.",
        "example_bad": """
# Recreates entire axes every frame!
scene = always_redraw(lambda: VGroup(
    Axes(x_range=[-3,3]),
    axes.plot(lambda x: k.get_value() * x)
))
""",
        "example_good": """
# Only redraw the graph, not the axes
axes = Axes(x_range=[-3, 3, 1], y_range=[-3, 3, 1])
graph = always_redraw(lambda: axes.plot(
    lambda x: k.get_value() * x, color=BLUE))
""",
    },

    # ── 5.3  Very long Text() strings ──────────────────────────────────────
    {
        "id": "long_text_slow",
        "symptom": "Text creation takes >30 seconds",
        "root_cause": (
            "Text() uses Pango/SVG rendering. Very long strings (>500 chars) "
            "create huge SVG files that are slow to parse."
        ),
        "fix": "Break text into multiple shorter Text objects.",
    },

    # ── 5.4  Too many simultaneous animations ─────────────────────────────
    {
        "id": "too_many_anims",
        "symptom": "Frame rate drops; render is slow",
        "root_cause": (
            "self.play(anim1, anim2, anim3, ... anim100) with many objects "
            "forces interpolation of all objects every frame."
        ),
        "fix": "Use LaggedStartMap or AnimationGroup to batch animations.",
    },

    # ── 5.5  MathTex created inside always_redraw ─────────────────────────
    {
        "id": "mathtex_in_always_redraw",
        "symptom": "Render is extremely slow (minutes per second of video)",
        "root_cause": (
            "MathTex requires LaTeX compilation. Creating it inside "
            "always_redraw() compiles LaTeX EVERY FRAME (30 or 60 times per second)."
        ),
        "fix": "Use DecimalNumber for dynamic values, or update text with become().",
        "example_bad": """
label = always_redraw(lambda: MathTex(
    f"x = {tracker.get_value():.2f}"))  # LaTeX compiles every frame!
""",
        "example_good": """
# Option 1: Use DecimalNumber (no LaTeX, fast)
label = DecimalNumber(0, num_decimal_places=2)
label.add_updater(lambda m: m.set_value(tracker.get_value()))

# Option 2: Use Text (faster than MathTex for plain numbers)
label = always_redraw(lambda: Text(
    f"x = {tracker.get_value():.2f}", font_size=24))
""",
    },
]


# =============================================================================
# CATEGORY 6: OBJECT LIFECYCLE / CLEANUP BUGS
# =============================================================================

LIFECYCLE_BUGS = [

    # ── 6.1  Double-adding an object ───────────────────────────────────────
    {
        "id": "double_add",
        "symptom": "Object appears at double opacity or duplicate rendering",
        "root_cause": "self.add(obj) followed by self.play(FadeIn(obj)) adds it twice.",
        "fix": "Use only one: either self.add() for instant, or FadeIn() for animated.",
    },

    # ── 6.2  FadeOut on group doesn't clean submobjects ───────────────────
    {
        "id": "fadeout_group_submobjects",
        "symptom": "Submobjects still visible after FadeOut(group)",
        "root_cause": (
            "If you separately added submobjects AND the group, FadeOut(group) "
            "only removes the group reference, not the individual adds."
        ),
        "fix": "Only add the VGroup, never the individual submobjects.",
    },

    # ── 6.3  Using self.remove() without fade ─────────────────────────────
    {
        "id": "abrupt_remove",
        "symptom": "Objects pop out abruptly in the video",
        "root_cause": "self.remove(obj) is instant. It doesn't animate.",
        "fix": "Use self.play(FadeOut(obj)) for smooth removal.",
    },

    # ── 6.4  Updater still running after object removed ────────────────────
    {
        "id": "orphan_updater",
        "symptom": "Errors about accessing removed objects",
        "root_cause": "always_redraw objects still reference removed mobjects.",
        "fix": "Remove the always_redraw object before removing the mobjects it depends on.",
    },
]


# =============================================================================
# CATEGORY 7: COORDINATE / POSITIONING BUGS
# =============================================================================

POSITIONING_BUGS = [

    # ── 7.1  Axes too large, clips out of frame ───────────────────────────
    {
        "id": "axes_too_large",
        "symptom": "Graph extends past visible area; axis labels not visible",
        "root_cause": (
            "Default Axes x_length/y_length can be too big when combined with "
            "title and caption zones."
        ),
        "fix": "Use x_length=7, y_length=3.0-3.5, and shift(DOWN*0.4).",
        "example_good": """
axes = Axes(x_range=[-4, 4, 1], y_range=[-1, 4, 1],
            x_length=7, y_length=3.2,
            axis_config={"stroke_width": 2})
axes.shift(DOWN * 0.4)
""",
    },

    # ── 7.2  Title overlapping with content ────────────────────────────────
    {
        "id": "title_overlap",
        "symptom": "Title text rendered on top of graphs/equations",
        "root_cause": "Title placed at ORIGIN or UP*1 instead of to_edge(UP).",
        "fix": "title.to_edge(UP, buff=0.3). Keep content below y=3.0.",
    },

    # ── 7.3  to_edge vs to_corner confusion ───────────────────────────────
    {
        "id": "to_edge_confusion",
        "symptom": "Object not at expected position",
        "root_cause": "to_edge(UP) centers horizontally; to_corner(UL) puts at corner.",
    },

    # ── 7.4  Frame coordinates vs graph coordinates ────────────────────────
    {
        "id": "coordinate_confusion",
        "symptom": "Dot appears at wrong position on graph",
        "root_cause": (
            "Using Dot(point=[x, y, 0]) when you meant Dot(axes.c2p(x, y)). "
            "Frame coordinates are in Manim units (-7 to 7 horizontally), "
            "while graph coordinates need c2p() conversion."
        ),
        "fix": "Always use axes.c2p(x, y) for points on a graph.",
    },

    # ── 7.5  next_to with large buff pushes off screen ─────────────────────
    {
        "id": "next_to_offscreen",
        "symptom": "Label or annotation not visible",
        "root_cause": "next_to(obj, UP, buff=3) can push labels above the visible frame.",
        "fix": "Use small buff values (0.1-0.5) and check positioning.",
    },
]


# =============================================================================
# CATEGORY 8: COLOR / STYLING BUGS
# =============================================================================

COLOR_BUGS = [

    # ── 8.1  Using old color constants ─────────────────────────────────────
    {
        "id": "old_color_constants",
        "symptom": "NameError: BLUE_E, TEAL_C, etc. not found",
        "root_cause": (
            "Some manimgl color shades (BLUE_E, RED_A, etc.) may not be "
            "defined in Manim CE's namespace."
        ),
        "fix": "Use Manim CE's ManimColor or hex strings.",
    },

    # ── 8.2  set_color after adding to scene ───────────────────────────────
    {
        "id": "set_color_after_add",
        "symptom": "Color change not visible",
        "root_cause": "Some styling changes don't propagate after the object is rendered.",
        "fix": "Set color before adding to scene, or use animate: obj.animate.set_color(RED).",
    },

    # ── 8.3  fill_opacity without fill_color ───────────────────────────────
    {
        "id": "fill_opacity_no_color",
        "symptom": "Shape appears solid black instead of transparent colored",
        "root_cause": "fill_opacity=1 with no fill_color defaults to black.",
        "fix": "Always specify both fill_color and fill_opacity together.",
    },
]


# =============================================================================
# CATEGORY 9: IMPORT / MODULE ISSUES
# =============================================================================

IMPORT_ISSUES = [

    # ── 9.1  from manim import * doesn't get everything ───────────────────
    {
        "id": "star_import_missing",
        "symptom": "NameError for less common classes like Arrow3D, Surface, etc.",
        "root_cause": (
            "'from manim import *' only imports what's in __all__. Some classes "
            "like ParametricSurface, Arrow3D need explicit imports."
        ),
        "fix": "Explicitly import needed classes: from manim.mobject.three_d import ...",
    },

    # ── 9.2  Importing from wrong submodule ────────────────────────────────
    {
        "id": "wrong_submodule",
        "symptom": "ImportError: cannot import name 'X' from 'manim'",
        "root_cause": "Some utilities need explicit path imports.",
    },

    # ── 9.3  np not imported ───────────────────────────────────────────────
    {
        "id": "missing_numpy_import",
        "symptom": "NameError: name 'np' is not defined",
        "root_cause": "Script uses np.sin, np.maximum etc. but forgot to import numpy.",
        "fix": "Ensure 'import numpy as np' is present.",
        "regex_fix": r"""
# If code uses np. but doesn't import it
if 'np.' in code and 'import numpy' not in code:
    code = 'import numpy as np\n' + code
""",
        "sanitize_priority": "CRITICAL",
    },

    # ── 9.4  random imports (security + determinism) ───────────────────────
    {
        "id": "random_imports",
        "symptom": "Non-deterministic renders; potential security issue",
        "root_cause": "Claude may import random, os, subprocess, etc.",
        "fix": "Whitelist allowed imports: manim, numpy, app.manim_pipeline.styles.",
        "regex_fix": r"""
# Remove dangerous imports
re.sub(r'^import\s+(os|sys|subprocess|shutil|pathlib|random).*$', '', code, flags=re.MULTILINE)
re.sub(r'^from\s+(os|sys|subprocess|shutil|pathlib|random)\s+import.*$', '', code, flags=re.MULTILINE)
""",
        "sanitize_priority": "CRITICAL",
    },

    # ── 9.5  Missing OctoflashScene import for no-voice scripts ────────────
    {
        "id": "octoflash_import_no_voice",
        "symptom": "NameError: name 'OctoflashScene' is not defined",
        "root_cause": (
            "Claude generates no-voice script but still references OctoflashScene "
            "in imports or class definition."
        ),
        "fix": "strip_voiceover() should catch this; verify.",
    },

    # ── 9.6  Importing Scene from styles instead of manim ──────────────────
    {
        "id": "scene_from_styles",
        "symptom": "ImportError: cannot import name 'Scene' from 'app.manim_pipeline.styles'",
        "root_cause": "Styles module exports OctoflashScene, not Scene. Scene is from manim.",
        "fix": "Detect and fix this import pattern.",
        "regex_fix": r"""
# Fix importing Scene from styles (it's from manim)
re.sub(
    r'from app\.manim_pipeline\.styles import \(([^)]*\b)Scene\b',
    fix_scene_import,
    code
)
""",
        "sanitize_priority": "HIGH",
    },
]


# =============================================================================
# COMPREHENSIVE sanitize_script() IMPLEMENTATION
# =============================================================================

def sanitize_script(code: str) -> str:
    """Auto-fix common Claude mistakes that crash Manim CE rendering.

    This function applies all safe, regex-based fixes from the reference above.
    Fixes are ordered by priority: CRITICAL > HIGH > MEDIUM > LOW.
    """

    # ── CRITICAL FIXES ──────────────────────────────────────────────────────

    # 1.6: ShowCreation → Create
    code = re.sub(r'\bShowCreation\b', 'Create', code)

    # 1.7: get_graph() → plot()
    code = re.sub(r'\.get_graph\(', '.plot(', code)

    # 1.9: TexMobject → MathTex, TextMobject → Text
    code = re.sub(r'\bTexMobject\b', 'MathTex', code)
    code = re.sub(r'\bTextMobject\b', 'Text', code)

    # 1.3/1.4: max()/min() in lambdas → np.maximum()/np.minimum()
    # Handle: lambda x: max(0, x) and nested variants
    code = re.sub(
        r'(lambda\s+\w+\s*:.*)(?<!\w)max\(',
        lambda m: m.group(0).replace('max(', 'np.maximum(', 1),
        code,
    )
    code = re.sub(
        r'(lambda\s+\w+\s*:.*)(?<!\w)min\(',
        lambda m: m.group(0).replace('min(', 'np.minimum(', 1),
        code,
    )

    # 1.21: math.* → np.* (and remove import math)
    code = re.sub(r'\bmath\.sin\b', 'np.sin', code)
    code = re.sub(r'\bmath\.cos\b', 'np.cos', code)
    code = re.sub(r'\bmath\.tan\b', 'np.tan', code)
    code = re.sub(r'\bmath\.exp\b', 'np.exp', code)
    code = re.sub(r'\bmath\.log\b', 'np.log', code)
    code = re.sub(r'\bmath\.sqrt\b', 'np.sqrt', code)
    code = re.sub(r'\bmath\.pi\b', 'np.pi', code)
    code = re.sub(r'\bmath\.e(?!\w)\b', 'np.e', code)
    code = re.sub(r'\bmath\.floor\b', 'np.floor', code)
    code = re.sub(r'\bmath\.ceil\b', 'np.ceil', code)
    code = re.sub(r'\bmath\.pow\b', 'np.power', code)
    code = re.sub(r'\bmath\.fabs\b', 'np.abs', code)
    code = re.sub(r'^\s*import\s+math\s*$', '', code, flags=re.MULTILINE)

    # 9.3: Ensure numpy is imported if used
    if 'np.' in code and 'import numpy' not in code:
        # Insert after the first import line
        code = re.sub(
            r'(^(?:from|import)\s+.+$)',
            r'\1\nimport numpy as np',
            code,
            count=1,
            flags=re.MULTILINE,
        )

    # 9.4: Remove dangerous imports
    code = re.sub(
        r'^\s*import\s+(os|sys|subprocess|shutil|pathlib|random|socket|urllib|requests|http)\b.*$',
        '',
        code,
        flags=re.MULTILINE,
    )
    code = re.sub(
        r'^\s*from\s+(os|sys|subprocess|shutil|pathlib|random|socket|urllib|requests|http)\b\s+import.*$',
        '',
        code,
        flags=re.MULTILINE,
    )

    # ── HIGH FIXES ──────────────────────────────────────────────────────────

    # 1.10: Remove move_camera and set_camera_orientation (2D scenes only)
    # Only remove if the scene class doesn't inherit from ThreeDScene
    if 'ThreeDScene' not in code and 'Octoflash3DScene' not in code:
        code = re.sub(r'^\s*self\.move_camera\(.*?\)\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^\s*self\.set_camera_orientation\(.*?\)\s*$', '', code, flags=re.MULTILINE)

    # 1.11: ThreeDAxes → Axes (if no ThreeDScene)
    if 'ThreeDScene' not in code and 'Octoflash3DScene' not in code:
        code = re.sub(r'\bThreeDAxes\b', 'Axes', code)

    # 1.14: Remove $ signs from MathTex
    code = re.sub(
        r"""(MathTex\(\s*r?["'])\$(.*?)\$(["'])""",
        r'\1\2\3',
        code,
    )

    # 1.19: Fix hex colors without #
    code = re.sub(
        r"""(color\s*=\s*['\"])([0-9a-fA-F]{6})(['\"])""",
        r"\1#\2\3",
        code,
    )

    # 9.6: Fix importing Scene from styles
    if 'from app.manim_pipeline.styles import' in code:
        # If Scene is in the styles import, move it to manim import
        styles_import_match = re.search(
            r'from app\.manim_pipeline\.styles import \(([^)]*)\)',
            code,
            re.DOTALL,
        )
        if styles_import_match:
            imports_text = styles_import_match.group(1)
            if re.search(r'\bScene\b', imports_text) and 'OctoflashScene' not in imports_text:
                # Remove Scene from styles import
                new_imports = re.sub(r',?\s*\bScene\b\s*,?', ',', imports_text)
                new_imports = re.sub(r',\s*,', ',', new_imports)
                new_imports = re.sub(r'^\s*,', '', new_imports)
                new_imports = re.sub(r',\s*$', '', new_imports)
                code = code.replace(imports_text, new_imports)

    # ── MEDIUM FIXES ────────────────────────────────────────────────────────

    # 2.5: Old FadeIn/FadeOut variants
    code = re.sub(r'\bFadeInFromDown\b', 'FadeIn', code)
    code = re.sub(r'\bFadeInFromLarge\b', 'FadeIn', code)
    code = re.sub(r'\bFadeOutAndShift\b', 'FadeOut', code)
    code = re.sub(r'\bFadeOutAndShiftDown\b', 'FadeOut', code)

    # 2.7: play_all → play
    code = re.sub(r'\bself\.play_all\b', 'self.play', code)

    # 2.15: Remove self.embed()
    code = re.sub(r'^\s*self\.embed\(\)\s*$', '', code, flags=re.MULTILINE)

    # 2.12: Remove add_fixed_in_frame_mobjects (2D only)
    if 'ThreeDScene' not in code:
        code = re.sub(
            r'^\s*self\.add_fixed_in_frame_mobjects?\(.*?\)\s*$',
            '',
            code,
            flags=re.MULTILINE,
        )

    # ── LOW FIXES ───────────────────────────────────────────────────────────

    # 1.15: Remove custom font specifications
    code = re.sub(r',\s*font\s*=\s*["\'][^"\']*["\']', '', code)

    # Clean up blank lines from removed code (max 2 consecutive)
    code = re.sub(r'\n{4,}', '\n\n\n', code)

    return code


# =============================================================================
# QUICK REFERENCE: Error → Fix lookup table
# =============================================================================

ERROR_TO_FIX = {
    "ShowCreation": "Replace with Create",
    "get_graph": "Replace with .plot()",
    "TexMobject": "Replace with MathTex",
    "TextMobject": "Replace with Text",
    "max(0, x) in lambda": "Replace with np.maximum(0, x)",
    "min(1, x) in lambda": "Replace with np.minimum(1, x)",
    "math.sin": "Replace with np.sin (and remove import math)",
    "move_camera on 2D": "Remove the line entirely",
    "ThreeDAxes on 2D": "Replace with Axes",
    "$ in MathTex": "Remove the $ signs",
    "hex color without #": "Prepend # to the color string",
    "FadeInFromDown": "Replace with FadeIn(shift=DOWN)",
    "import os/sys/subprocess": "Remove dangerous imports",
    "np not imported": "Add 'import numpy as np'",
    "float NaN": "Clamp function domain or use np.where",
    "empty VGroup animation": "Guard with if group check",
    "negative run_time": "Clamp to minimum 0.1",
    "LaTeX $ in MathTex": "MathTex is already in math mode",
}


if __name__ == "__main__":
    # Print a summary of all issues
    all_issues = (
        RENDERING_ERRORS + API_DIFFERENCES + ANIMATION_MISTAKES +
        TEXT_LATEX_ISSUES + PERFORMANCE_ISSUES + LIFECYCLE_BUGS +
        POSITIONING_BUGS + COLOR_BUGS + IMPORT_ISSUES
    )

    print(f"Total documented issues: {len(all_issues)}")
    print(f"\nBy category:")
    print(f"  Rendering errors: {len(RENDERING_ERRORS)}")
    print(f"  API differences:  {len(API_DIFFERENCES)}")
    print(f"  Animation mistakes: {len(ANIMATION_MISTAKES)}")
    print(f"  Text/LaTeX issues: {len(TEXT_LATEX_ISSUES)}")
    print(f"  Performance issues: {len(PERFORMANCE_ISSUES)}")
    print(f"  Lifecycle bugs:   {len(LIFECYCLE_BUGS)}")
    print(f"  Positioning bugs: {len(POSITIONING_BUGS)}")
    print(f"  Color/styling:    {len(COLOR_BUGS)}")
    print(f"  Import issues:    {len(IMPORT_ISSUES)}")

    # Count how many have regex fixes
    fixable = sum(1 for issue in all_issues if issue.get("regex_fix"))
    print(f"\nAuto-fixable (regex): {fixable}/{len(all_issues)}")
