# Manim CE Comprehensive Bug, Error, and Fix Reference

Complete reference of every common Manim Community Edition bug, error message, root cause, and fix. Organized for use as a sanitization and validation layer in AI-generated Manim scripts.

---

## TABLE OF CONTENTS

1. [Empty String / Empty Mobject Errors](#1-empty-string--empty-mobject-errors)
2. [LaTeX Compilation Errors](#2-latex-compilation-errors)
3. [TeX Installation / dvisvgm Errors](#3-tex-installation--dvisvgm-errors)
4. [Import Errors: manimlib vs manim (CE)](#4-import-errors-manimlib-vs-manim-ce)
5. [API Differences: 3b1b manim (manimlib) vs Manim CE](#5-api-differences-3b1b-manim-manimlib-vs-manim-ce)
6. [Animation Type Errors](#6-animation-type-errors)
7. [Scene.play() Errors](#7-sceneplay-errors)
8. [Mobject Errors](#8-mobject-errors)
9. [Coordinate System / Axes / Graphing Errors](#9-coordinate-system--axes--graphing-errors)
10. [Text and Font Errors](#10-text-and-font-errors)
11. [Resolution / Aspect Ratio Issues](#11-resolution--aspect-ratio-issues)
12. [Common Script Generation Errors](#12-common-script-generation-errors)
13. [Voiceover / Audio Sync Issues](#13-voiceover--audio-sync-issues)
14. [Performance Issues](#14-performance-issues)
15. [LaTeX Command Compatibility](#15-latex-command-compatibility)
16. [Color and Styling Errors](#16-color-and-styling-errors)
17. [Camera and 3D Errors](#17-camera-and-3d-errors)
18. [Updater and ValueTracker Errors](#18-updater-and-valuetracker-errors)
19. [File and Rendering Pipeline Errors](#19-file-and-rendering-pipeline-errors)
20. [Complete Sanitization Regex Reference](#20-complete-sanitization-regex-reference)

---

## 1. Empty String / Empty Mobject Errors

### 1.1 "Cannot create a mobject from an empty string"

**Exact error:**
```
ValueError: Cannot create a mobject from an empty string
```

**Root cause:** Passing an empty string `""` to `Text()`, `Tex()`, or `MathTex()`. Internally, Manim tries to render the string through Pango (for `Text`) or LaTeX (for `Tex`/`MathTex`), and empty input causes a failure.

**Fix:**
```python
# BAD
label = Text("")
formula = MathTex("")

# GOOD - guard against empty strings
label = Text(" ") if not text_content else Text(text_content)
formula = MathTex(r"\quad") if not tex_content else MathTex(tex_content)
```

**Sanitization regex:**
```python
# Replace empty Text/MathTex/Tex constructors
code = re.sub(r'Text\(\s*""\s*\)', 'Text(" ")', code)
code = re.sub(r"Text\(\s*''\s*\)", "Text(' ')", code)
code = re.sub(r'MathTex\(\s*""\s*\)', r'MathTex(r"\\quad")', code)
code = re.sub(r'Tex\(\s*""\s*\)', r'Tex(r"\\quad")', code)
```

### 1.2 "The text mobject does not seem to contain any characters"

**Exact error:**
```
ValueError: The text mobject Text('') does not seem to contain any characters.
```

**Root cause:** Passing an empty `Text` to `AddTextLetterByLetter` or `TypeWithCursor`. The animation checks `family_members_with_points()` and finds nothing.

**Fix:**
```python
# BAD
self.play(AddTextLetterByLetter(Text("")))

# GOOD - ensure non-empty
text = Text("Hello")
if text.family_members_with_points():
    self.play(AddTextLetterByLetter(text))
```

### 1.3 Empty VGroup passed to animations

**Exact error:**
```
ValueError: Called Scene.play with no animations
```
or a silent black frame.

**Root cause:** Creating an empty `VGroup()` and trying to animate it, or building a VGroup from a list comprehension that produces zero items.

**Fix:**
```python
# BAD
items = VGroup(*[Text(x) for x in some_list])  # some_list might be empty
self.play(FadeIn(items))

# GOOD
if some_list:
    items = VGroup(*[Text(x) for x in some_list])
    self.play(FadeIn(items))
```

---

## 2. LaTeX Compilation Errors

### 2.1 Generic LaTeX compilation failure

**Exact error:**
```
ValueError: latex error converting to dvi. See log output above or the log file: /path/to/file.log
```
or:
```
ValueError: pdflatex error converting to pdf. See log output above or the log file: /path/to/file.log
```

**Root cause:** Invalid LaTeX in `MathTex()` or `Tex()` string. The TeX compiler runs and exits with non-zero code.

**Common sub-causes and fixes:**

#### 2.1a Unescaped special characters

```python
# BAD - % is a comment character in LaTeX
MathTex("50%")
MathTex("x & y")
MathTex("cost = $5")

# GOOD
MathTex(r"50\%")
MathTex(r"x \& y")
MathTex(r"\text{cost} = \$5")
```

#### 2.1b Missing raw string prefix

```python
# BAD - Python interprets \f as a form feed character
MathTex("\frac{1}{2}")

# GOOD - always use raw strings for LaTeX
MathTex(r"\frac{1}{2}")
```

#### 2.1c Unmatched braces

```python
# BAD
MathTex(r"e^{i\tau} = 1")  # This actually works
MathTex(r"e^{i", r"\tau} = 1")  # Split across args - Manim handles this

# BAD - genuinely unmatched
MathTex(r"\frac{1}{2")  # Missing closing brace

# GOOD
MathTex(r"\frac{1}{2}")
```

**Note:** Manim CE has `_remove_stray_braces()` that adds missing `{` or `}` to balance, but this does not fix all cases.

#### 2.1d Invalid LaTeX commands

```python
# BAD - not a real LaTeX command without amsmath
MathTex(r"\R")
MathTex(r"\N")

# GOOD - use standard alternatives
MathTex(r"\mathbb{R}")
MathTex(r"\mathbb{N}")
```

#### 2.1e Unsupported packages

```python
# BAD - Manim's default TeX template may not include this package
MathTex(r"\usepackage{tikz}")  # Not valid inside MathTex

# GOOD - use custom tex_template
from manim import TexTemplate
template = TexTemplate()
template.add_to_preamble(r"\usepackage{tikz}")
MathTex(r"...", tex_template=template)
```

### 2.2 "TexTemplate does not support character"

**Exact error:**
```
TexTemplate does not support character 'LATIN SMALL LETTER A WITH ACUTE' (U+00E1).
```

**Root cause:** The default LaTeX template uses `inputenc` which does not support certain Unicode characters.

**Fix:**
```python
# Option 1: Use lualatex which supports Unicode natively
from manim import TexTemplate
template = TexTemplate(tex_compiler="lualatex", output_format=".pdf")
MathTex(r"\text{caf\'{e}}", tex_template=template)

# Option 2: Use Text() instead of Tex() for non-math Unicode
Text("cafe", font_size=36)
```

### 2.3 "You do not have package X installed"

**Exact error:**
```
You do not have package cancel installed.
Install cancel it using your LaTeX package manager, or check for typos.
```

**Root cause:** The LaTeX expression uses a package not installed on the system.

**Fix:** Install the missing package via system package manager, or avoid using commands from that package.

### 2.4 Font size must be greater than 0

**Exact error:**
```
ValueError: font_size must be greater than 0.
```

**Root cause:** Setting `font_size=0` or a negative value on `MathTex`, `Tex`, `SingleStringMathTex`.

**Fix:**
```python
# BAD
MathTex(r"x", font_size=0)

# GOOD
MathTex(r"x", font_size=24)
```

---

## 3. TeX Installation / dvisvgm Errors

### 3.1 "No TeX installation found" / LaTeX not on PATH

**Exact error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'latex'
```
or:
```
RuntimeError: latex failed but did not produce a log file. Check your LaTeX installation.
```

**Root cause:** LaTeX (pdflatex, lualatex, or xelatex) is not installed or not on PATH.

**Fix:**
- macOS: `brew install --cask mactex-no-gui` or `brew install basictex`
- Ubuntu/Debian: `sudo apt-get install texlive-full` or `sudo apt-get install texlive-latex-extra`
- Windows: Install MiKTeX or TeX Live
- Docker: `apt-get install texlive texlive-latex-extra`

### 3.2 "Your installation does not support converting X files to SVG"

**Exact error:**
```
ValueError: Your installation does not support converting .dvi files to SVG. Consider updating dvisvgm to at least version 2.4.
```

**Root cause:** `dvisvgm` is not installed, too old, or cannot convert the output format.

**Fix:**
- Update dvisvgm: `brew install dvisvgm` (macOS) or install via TeX Live
- Check version: `dvisvgm --version` (need >= 2.4)
- For PDF output: need dvisvgm compiled with Ghostscript support

### 3.3 "Tex compiler X unknown"

**Exact error:**
```
ValueError: Tex compiler mytex unknown.
```

**Root cause:** Invalid `tex_compiler` value in `TexTemplate`. Valid values: `latex`, `pdflatex`, `luatex`, `lualatex`, `xelatex`.

**Fix:**
```python
# GOOD
template = TexTemplate(tex_compiler="pdflatex", output_format=".dvi")
template = TexTemplate(tex_compiler="lualatex", output_format=".pdf")
template = TexTemplate(tex_compiler="xelatex", output_format=".xdv")
```

---

## 4. Import Errors: manimlib vs manim (CE)

### 4.1 "ModuleNotFoundError: No module named 'manimlib'"

**Exact error:**
```
ModuleNotFoundError: No module named 'manimlib'
```

**Root cause:** Script was written for 3b1b's manim (manimlib) but Manim CE (manim) is installed.

**Fix:**
```python
# BAD (3b1b manim / manimlib)
from manimlib.imports import *
from manimlib import *

# GOOD (Manim CE)
from manim import *
```

### 4.2 "ImportError: cannot import name 'ShowCreation'"

**Exact error:**
```
ImportError: cannot import name 'ShowCreation' from 'manim'
```

**Root cause:** `ShowCreation` was renamed to `Create` in Manim CE.

**Fix:**
```python
# BAD
from manim import ShowCreation
self.play(ShowCreation(circle))

# GOOD
from manim import Create
self.play(Create(circle))
```

**Sanitization regex:**
```python
code = re.sub(r'\bShowCreation\b', 'Create', code)
```

### 4.3 "ImportError: cannot import name 'ShowPassingFlashAround'"

**Exact error:**
```
ImportError: cannot import name 'ShowPassingFlashAround' from 'manim'
```

**Root cause:** Removed in Manim CE. Use `ShowPassingFlash` or `Circumscribe` instead.

**Fix:**
```python
# BAD
self.play(ShowPassingFlashAround(mobject))

# GOOD
self.play(Circumscribe(mobject))
# or
self.play(ShowPassingFlash(mobject.copy().set_stroke(YELLOW, 3)))
```

### 4.4 "ImportError: cannot import name 'TextMobject'"

**Exact error:**
```
ImportError: cannot import name 'TextMobject' from 'manim'
```

**Root cause:** `TextMobject` was renamed to `Tex` in Manim CE.

**Fix:**
```python
# BAD
TextMobject("Hello World")

# GOOD
Tex("Hello World")
```

### 4.5 "ImportError: cannot import name 'TexMobject'"

**Exact error:**
```
ImportError: cannot import name 'TexMobject' from 'manim'
```

**Root cause:** `TexMobject` was renamed to `MathTex` in Manim CE.

**Fix:**
```python
# BAD
TexMobject(r"\int_0^1 x\,dx")

# GOOD
MathTex(r"\int_0^1 x\,dx")
```

---

## 5. API Differences: 3b1b manim (manimlib) vs Manim CE

### COMPLETE RENAMED CLASSES AND METHODS

| manimlib (3b1b) | Manim CE | Notes |
|---|---|---|
| `ShowCreation` | `Create` | Animation |
| `Uncreate` (if custom) | `Uncreate` | Same name, works in CE |
| `TextMobject` | `Tex` | LaTeX text |
| `TexMobject` | `MathTex` | LaTeX math |
| `get_graph()` | `plot()` | On Axes/CoordinateSystem |
| `get_graph_label()` | `get_graph_label()` | Same name, still in CE |
| `GraphScene` | Removed | Use `Axes` inside `Scene` |
| `ShowPassingFlashAround` | `Circumscribe` | Indication animation |
| `FadeInFromDown` | `FadeIn(shift=UP)` | Directional fade |
| `FadeInFromLarge` | `FadeIn(scale=0.5)` | Scale fade |
| `FadeOutAndShift` | `FadeOut(shift=DOWN)` | Directional fade out |
| `FadeOutAndShiftDown` | `FadeOut(shift=DOWN)` | Directional fade out |
| `FadeInFrom` | `FadeIn(shift=...)` | Use shift parameter |
| `FadeInFromPoint` | `FadeIn(target_position=...)` | Use target_position |
| `GrowFromCenter` | `GrowFromCenter` | Same in CE |
| `GrowArrow` | `GrowArrow` | Same in CE |
| `SpinInFromNothing` | `SpinInFromNothing` | Same in CE |
| `UpdateFromFunc` | `UpdateFromFunc` | Same in CE |
| `UpdateFromAlphaFunc` | `UpdateFromAlphaFunc` | Same in CE |
| `LaggedStartMap` | `LaggedStartMap` | Same in CE |
| `LaggedStart` | `LaggedStart` | Same in CE |
| `AnimationGroup` | `AnimationGroup` | Same in CE |
| `Succession` | `Succession` | Same in CE |
| `TransformMatchingTex` | `TransformMatchingTex` | Same in CE |
| `TransformMatchingShapes` | `TransformMatchingShapes` | Same in CE |
| `self.camera.frame` | `self.camera.frame` | MovingCameraScene |
| `NumberPlane` | `NumberPlane` | Same in CE |
| `ThreeDAxes` | `ThreeDAxes` | Same in CE |
| `ParametricSurface` | `Surface` | Renamed |
| `always_redraw` | `always_redraw` | Same in CE |
| `DecimalNumber` | `DecimalNumber` | Same in CE |
| `Integer` | `Integer` | Same in CE |
| `play_all()` | Not in CE | Use `AnimationGroup` |
| `Scene.setup()` | `Scene.setup()` | Same in CE |

### 5.1 get_graph() -> plot()

**Exact error:**
```
AttributeError: 'Axes' object has no attribute 'get_graph'
```

**Root cause:** 3b1b manim uses `axes.get_graph()`, Manim CE uses `axes.plot()`.

**Fix:**
```python
# BAD (manimlib)
graph = axes.get_graph(lambda x: x**2)
graph = axes.get_graph(lambda x: np.sin(x), color=BLUE)

# GOOD (Manim CE)
graph = axes.plot(lambda x: x**2)
graph = axes.plot(lambda x: np.sin(x), color=BLUE)
```

**Sanitization regex:**
```python
code = re.sub(r'\.get_graph\(', '.plot(', code)
```

### 5.2 GraphScene removed

**Exact error:**
```
ImportError: cannot import name 'GraphScene' from 'manim'
```

**Root cause:** `GraphScene` was removed entirely in Manim CE.

**Fix:**
```python
# BAD (manimlib)
class MyScene(GraphScene):
    def __init__(self):
        GraphScene.__init__(self, x_min=-5, x_max=5)
    def construct(self):
        self.setup_axes()
        graph = self.get_graph(lambda x: x**2)

# GOOD (Manim CE)
class MyScene(Scene):
    def construct(self):
        axes = Axes(x_range=[-5, 5, 1], y_range=[-1, 25, 5],
                    x_length=7, y_length=5)
        graph = axes.plot(lambda x: x**2)
        self.play(Create(axes), Create(graph))
```

### 5.3 FadeInFromDown / FadeOutAndShift removed

**Exact error:**
```
ImportError: cannot import name 'FadeInFromDown' from 'manim'
```

**Root cause:** Directional fade variants were consolidated into `FadeIn`/`FadeOut` with `shift` parameter.

**Fix:**
```python
# BAD (manimlib)
self.play(FadeInFromDown(text))
self.play(FadeInFrom(text, LEFT))
self.play(FadeOutAndShift(text, UP))
self.play(FadeOutAndShiftDown(text))
self.play(FadeInFromLarge(text))

# GOOD (Manim CE)
self.play(FadeIn(text, shift=UP))
self.play(FadeIn(text, shift=RIGHT))  # note: from LEFT means shift RIGHT
self.play(FadeOut(text, shift=UP))
self.play(FadeOut(text, shift=DOWN))
self.play(FadeIn(text, scale=0.5))
```

**Sanitization regex:**
```python
code = re.sub(r'FadeInFromDown\(', 'FadeIn(shift=UP, mobject=', code)  # approximate
code = re.sub(r'FadeOutAndShift\((\w+),\s*(.*?)\)', r'FadeOut(\1, shift=\2)', code)
```

### 5.4 ParametricSurface -> Surface

**Exact error:**
```
ImportError: cannot import name 'ParametricSurface' from 'manim'
```

**Root cause:** Renamed in Manim CE.

**Fix:**
```python
# BAD
from manimlib import ParametricSurface
surface = ParametricSurface(func, u_range=[0, 1], v_range=[0, 1])

# GOOD
from manim import Surface
surface = Surface(func, u_range=[0, 1], v_range=[0, 1])
```

### 5.5 Passing methods to Scene.play()

**Exact error:**
```
TypeError: Passing Mobject methods to Scene.play is no longer supported. Use Mobject.animate instead.
```

**Root cause:** In manimlib, you could do `self.play(mob.shift, UP)`. In CE, use `.animate`.

**Fix:**
```python
# BAD (manimlib style)
self.play(circle.shift, UP)
self.play(circle.set_color, RED)
self.play(circle.scale, 2)

# GOOD (Manim CE)
self.play(circle.animate.shift(UP))
self.play(circle.animate.set_color(RED))
self.play(circle.animate.scale(2))
```

### 5.6 ApplyMethod deprecated patterns

**Exact error:**
```
TypeError: Unexpected argument ... passed to Scene.play().
```

**Root cause:** `ApplyMethod` still exists in CE but the `.animate` syntax is preferred.

**Fix:**
```python
# OLD (works but deprecated feel)
self.play(ApplyMethod(circle.shift, UP))

# GOOD
self.play(circle.animate.shift(UP))
```

### 5.7 REMOVED features in Manim CE

These features existed in manimlib but are NOT in Manim CE:

| Feature | Status | Alternative |
|---|---|---|
| `GraphScene` | Removed | Use `Axes` in `Scene` |
| `ShowPassingFlashAround` | Removed | `Circumscribe` |
| `FadeInFromDown` | Removed | `FadeIn(shift=UP)` |
| `FadeInFromLarge` | Removed | `FadeIn(scale=0.5)` |
| `FadeOutAndShift` | Removed | `FadeOut(shift=...)` |
| `FadeOutAndShiftDown` | Removed | `FadeOut(shift=DOWN)` |
| `FadeInFrom` | Removed | `FadeIn(shift=...)` |
| `FadeInFromPoint` | Removed | `FadeIn(target_position=...)` |
| `play_all()` | Removed | `AnimationGroup` |
| `TextMobject` | Removed | `Tex` |
| `TexMobject` | Removed | `MathTex` |
| `ShowCreation` | Removed | `Create` |
| `get_graph()` | Removed from Axes | `plot()` |
| `setup_axes()` | Removed (GraphScene) | Create `Axes()` directly |
| `ParametricSurface` | Removed | `Surface` |
| `ContinualAnimation` | Removed | Use updaters |
| `NormalAnimationAsContinualAnimation` | Removed | Use updaters |
| `scene.dither()` | Removed | `scene.wait()` |
| `digest_config()` | Removed | Use `__init__` params |
| `CONFIG` dict pattern | Removed | Use `__init__` params |

### 5.8 NEW features only in Manim CE

| Feature | Description |
|---|---|
| `.animate` syntax | `mob.animate.shift(UP)` |
| `Blink` animation | Cursor blink for typing |
| `TypeWithCursor` | Typing animation with cursor |
| `UntypeWithCursor` | Reverse typing with cursor |
| `Unwrite` | Reverse of `Write` |
| `SpiralIn` | Spiral entrance animation |
| `TransformMatchingShapes` | Shape-matching transform |
| `Circumscribe` | Highlight animation |
| `Wiggle` | Wiggle indication |
| `MovingCameraScene` | Built-in camera movement |
| `ZoomedScene` | Zoom effect |
| `Code` mobject | Syntax-highlighted code |
| `Table` mobject | Table rendering |
| `MarkupText` | Pango markup text |
| `BulletedList` | Tex-based bullet list |
| `Title` | Title convenience class |
| `ImplicitFunction` | Implicit function plotting |
| `BarChart` | Bar chart mobject |
| Boolean operations | `Union`, `Intersection`, `Difference`, `Exclusion` |
| `Labeled` geometry | `LabeledDot`, `LabeledLine`, `LabeledArrow` |

---

## 6. Animation Type Errors

### 6.1 "Create only works for VMobjects"

**Exact error:**
```
TypeError: Create only works for VMobjects.
```

**Root cause:** `Create` (and `ShowPartial`) requires a `VMobject`. Passing a `Group`, `ImageMobject`, or plain `Mobject` fails.

**Fix:**
```python
# BAD
img = ImageMobject("photo.png")
self.play(Create(img))

# GOOD - use FadeIn for non-VMobjects
self.play(FadeIn(img))

# For Groups of mixed types
self.play(FadeIn(group))
```

### 6.2 "DrawBorderThenFill only works for vectorized Mobjects"

**Exact error:**
```
TypeError: DrawBorderThenFill only works for vectorized Mobjects
```

**Root cause:** Same as above -- `Write` inherits from `DrawBorderThenFill`, which requires `VMobject`.

**Fix:**
```python
# BAD
self.play(Write(ImageMobject("img.png")))

# GOOD
self.play(Write(Text("Hello")))  # Text is a VMobject
self.play(FadeIn(ImageMobject("img.png")))  # FadeIn works on anything
```

### 6.3 "Animation only works on Mobjects"

**Exact error:**
```
TypeError: Animation only works on Mobjects
```

**Root cause:** Passing a non-Mobject (string, number, list, etc.) to an animation.

**Fix:**
```python
# BAD
self.play(FadeIn("hello"))
self.play(FadeIn([circle, square]))

# GOOD
self.play(FadeIn(Text("hello")))
self.play(FadeIn(VGroup(circle, square)))
```

### 6.4 "Object X cannot be converted to an animation"

**Exact error:**
```
TypeError: Object 42 cannot be converted to an animation
```

**Root cause:** Passing something that is neither an `Animation` nor a valid `.animate` call to `self.play()`.

**Fix:**
```python
# BAD
self.play(42)
self.play(circle)  # mobject, not animation
self.play(lambda: circle.shift(UP))

# GOOD
self.play(FadeIn(circle))
self.play(circle.animate.shift(UP))
```

### 6.5 "The run_time of X cannot be negative"

**Exact error:**
```
ValueError: The run_time of FadeIn cannot be negative. The given value was -1.
```

**Root cause:** Passing a negative `run_time` to an animation, often from a calculation like `tracker.get_remaining_duration()` returning negative.

**Fix:**
```python
# BAD
remaining = tracker.get_remaining_duration(buff=-0.3)
self.wait(remaining)  # remaining might be negative

# GOOD
remaining = tracker.get_remaining_duration(buff=-0.3)
if remaining > 0:
    self.wait(remaining)
```

---

## 7. Scene.play() Errors

### 7.1 "Called Scene.play with no animations"

**Exact error:**
```
ValueError: Called Scene.play with no animations
```

**Root cause:** Calling `self.play()` with an empty argument list or with arguments that all resolve to nothing.

**Fix:**
```python
# BAD
self.play()
self.play(*[])
animations = []
self.play(*animations)

# GOOD - check first
if animations:
    self.play(*animations)
```

### 7.2 "Unexpected argument X passed to Scene.play()"

**Exact error:**
```
TypeError: Unexpected argument <some_object> passed to Scene.play().
```

**Root cause:** Passing a non-animation, non-mobject-method object to `self.play()`.

**Fix:** Ensure every argument to `self.play()` is either:
- An `Animation` instance (`FadeIn(mob)`, `Create(mob)`, `Write(mob)`, etc.)
- A `.animate` call (`mob.animate.shift(UP)`)

### 7.3 "Specified mobjects cannot be None"

**Exact error:**
```
ValueError: Specified mobjects cannot be None
```

**Root cause:** Passing `None` to `self.add()` or `self.remove()`.

**Fix:**
```python
# BAD
self.add(None)
mob = some_function_that_might_return_none()
self.add(mob)

# GOOD
mob = some_function_that_might_return_none()
if mob is not None:
    self.add(mob)
```

### 7.4 "Could not find X in scene"

**Exact error:**
```
ValueError: Could not find <mobject> in scene
```

**Root cause:** Trying to `self.remove()` or replace a mobject that was never added to the scene.

**Fix:**
```python
# BAD - removing something not in scene
self.remove(circle)  # never added

# GOOD
self.add(circle)
# ... later
self.remove(circle)

# Or check first
if circle in self.mobjects:
    self.remove(circle)
```

---

## 8. Mobject Errors

### 8.1 "Only values of type Mobject can be added as submobjects"

**Exact error:**
```
TypeError: Only values of type Mobject can be added as submobjects of Mobject, but the value 3 (at index 0) is of type int.
```

**Root cause:** Adding a non-Mobject to a `VGroup` or as a submobject.

**Fix:**
```python
# BAD
VGroup(1, 2, 3)
VGroup("hello", circle)

# GOOD
VGroup(Text("1"), Text("2"), Text("3"))
VGroup(Text("hello"), circle)
```

### 8.2 "Cannot add Mobject as a submobject of itself"

**Exact error:**
```
ValueError: Cannot add Mobject as a submobject of itself (at index 0).
```

**Root cause:** `mob.add(mob)` -- adding a mobject to itself.

**Fix:**
```python
# BAD
group = VGroup()
group.add(group)

# GOOD
group = VGroup()
group.add(circle, square)
```

### 8.3 "Trying to restore without having saved"

**Exact error:**
```
Exception: Trying to restore without having saved
```

**Root cause:** Calling `mob.restore()` without first calling `mob.save_state()`.

**Fix:**
```python
# BAD
circle.restore()

# GOOD
circle.save_state()
self.play(circle.animate.shift(UP).set_color(RED))
self.play(Restore(circle))
```

### 8.4 "Too few rows and columns to fit all submobjects"

**Exact error:**
```
ValueError: Too few rows and columns to fit all submobjetcs.
```

**Root cause:** Using `mob.arrange_in_grid(rows=r, cols=c)` where `r * c < len(submobjects)`.

**Fix:**
```python
# BAD
group = VGroup(*[Square() for _ in range(10)])
group.arrange_in_grid(rows=2, cols=3)  # 2*3=6 < 10

# GOOD
group.arrange_in_grid(rows=4, cols=3)  # 4*3=12 >= 10
# or let it auto-calculate
group.arrange_in_grid(rows=4)
```

### 8.5 "Need at least one color"

**Exact error:**
```
ValueError: Need at least one color
```

**Root cause:** Passing an empty color list to `set_color_by_gradient()` or similar.

**Fix:**
```python
# BAD
mob.set_color_by_gradient()

# GOOD
mob.set_color_by_gradient(RED, BLUE)
```

### 8.6 MultiAnimationOverrideException

**Exact error:**
```
MultiAnimationOverrideException: ...
```

**Root cause:** Trying to override animation properties on a mobject that is already being animated.

**Fix:** Don't animate the same mobject in parallel with conflicting animations.

---

## 9. Coordinate System / Axes / Graphing Errors

### 9.1 axes.plot() with Python max()/min() inside lambda

**Exact error:**
```
ValueError: The truth value of an array with more than one element is ambiguous.
```

**Root cause:** Using Python's built-in `max()` or `min()` inside a lambda passed to `axes.plot()`. Manim may pass numpy arrays, and `max(0, array)` fails.

**Fix:**
```python
# BAD
graph = axes.plot(lambda x: max(0, x))
graph = axes.plot(lambda x: min(x, 5))

# GOOD - use numpy
graph = axes.plot(lambda x: np.maximum(0, x))
graph = axes.plot(lambda x: np.minimum(x, 5))
```

**Sanitization regex:**
```python
code = re.sub(r'lambda\s+x\s*:\s*max\(0,\s*x\)', 'lambda x: np.maximum(0, x)', code)
code = re.sub(r'lambda\s+x\s*:\s*min\(', 'lambda x: np.minimum(', code)
```

### 9.2 axes.plot() domain error (log, sqrt, division by zero)

**Exact error:**
```
RuntimeWarning: divide by zero encountered in double_scalars
```
or:
```
RuntimeWarning: invalid value encountered in sqrt
```
or blank/broken graph.

**Root cause:** The function hits a domain error (log of negative, sqrt of negative, division by zero).

**Fix:**
```python
# BAD
graph = axes.plot(lambda x: np.log(x), x_range=[-5, 5])
graph = axes.plot(lambda x: 1/x)

# GOOD - restrict domain
graph = axes.plot(lambda x: np.log(x), x_range=[0.01, 5, 0.01])
graph = axes.plot(lambda x: 1/x, x_range=[0.1, 5, 0.01], discontinuities=[0])
```

### 9.3 Axes x_range step size issues

**Exact error:** Axes renders but ticks are wrong, or very slow rendering.

**Root cause:** Missing step size in x_range/y_range, or step size too small.

**Fix:**
```python
# BAD - no step, defaults to 1
axes = Axes(x_range=[-10, 10])  # Only 20 ticks, ok
axes = Axes(x_range=[-100, 100])  # 200 ticks, slow

# BAD - step too small
axes = Axes(x_range=[-5, 5, 0.001])  # 10000 ticks!

# GOOD
axes = Axes(x_range=[-5, 5, 1], y_range=[-3, 3, 1])
```

### 9.4 c2p / coords_to_point returning wrong values

**Exact error:** Dots/labels appear at wrong positions.

**Root cause:** Using `c2p` without considering that Axes may be shifted/scaled.

**Fix:**
```python
# The c2p method accounts for the axes' position automatically
point = axes.c2p(2, 3)  # Correct - returns scene coordinates
dot = Dot(point=axes.c2p(2, 3))  # Correct

# BAD - manually computing position
dot = Dot(point=np.array([2, 3, 0]))  # Wrong if axes are shifted
```

### 9.5 get_area() with wrong graph reference

**Exact error:**
```
AttributeError: ...
```
or incorrect shading.

**Root cause:** Passing the wrong graph or bounds to `axes.get_area()`.

**Fix:**
```python
# GOOD
graph = axes.plot(lambda x: x**2)
area = axes.get_area(graph, x_range=[0, 2], color=BLUE, opacity=0.5)
```

### 9.6 get_riemann_rectangles() performance

**Root cause:** Too many rectangles makes rendering very slow.

**Fix:**
```python
# BAD - too many
rects = axes.get_riemann_rectangles(graph, x_range=[0, 5], dx=0.001)  # 5000 rects

# GOOD
rects = axes.get_riemann_rectangles(graph, x_range=[0, 5], dx=0.1)  # 50 rects
```

---

## 10. Text and Font Errors

### 10.1 Pango/cairo errors

**Exact error:**
```
OSError: no library called "cairo-2" was found
```
or:
```
OSError: dlopen("libpango-1.0.dylib"...): image not found
```

**Root cause:** Missing system dependencies for text rendering (Pango, Cairo).

**Fix:**
- macOS: `brew install pango cairo`
- Ubuntu: `sudo apt-get install libpango1.0-dev libcairo2-dev`

### 10.2 Font not found

**Exact error:**
```
WARNING: Pango could not find font "CustomFont". Using default.
```

**Root cause:** Specified font is not installed on the system.

**Fix:**
```python
# BAD
Text("Hello", font="NonExistentFont")

# GOOD - use available fonts
Text("Hello", font="Courier New")
Text("Hello")  # uses default font

# To register a custom font:
from manim import register_font
register_font("/path/to/font.ttf")
```

### 10.3 Text with newlines rendering issues

**Root cause:** `Text()` handles newlines differently than expected.

**Fix:**
```python
# For multi-line text, use Paragraph or explicit newlines
text = Text("Line 1\nLine 2\nLine 3")  # Works in CE

# Or use Paragraph
para = Paragraph("Line 1", "Line 2", "Line 3")
```

### 10.4 Text line_spacing parameter

**Exact error:** Text lines overlap or have too much spacing.

**Fix:**
```python
# Adjust line spacing
text = Text("Line 1\nLine 2", line_spacing=1.5)
```

### 10.5 Weight parameter errors

**Exact error:**
```
TypeError: ...
```

**Root cause:** Using invalid weight values.

**Fix:**
```python
# GOOD weights
Text("Bold", weight="BOLD")
Text("Normal", weight="NORMAL")
# Other valid weights: THIN, ULTRALIGHT, LIGHT, BOOK, MEDIUM, SEMIBOLD, ULTRABOLD, HEAVY, ULTRAHEAVY
```

---

## 11. Resolution / Aspect Ratio Issues

### 11.1 Default resolution confusion

**Root cause:** Manim CE default frame is 14.22 x 8.0 units (for 16:9 at 1920x1080). Objects positioned for different aspect ratios go off-screen.

**Key coordinates:**
```
Frame dimensions: 14.22 x 8.0 Manim units (at 1080p)
Center: ORIGIN = (0, 0, 0)
Top edge: y = 4.0
Bottom edge: y = -4.0
Left edge: x = -7.11
Right edge: x = 7.11
```

### 11.2 Objects off-screen after scaling

**Fix:**
```python
# Always check bounds after positioning
mob.to_edge(UP, buff=0.5)  # safe top
mob.to_edge(DOWN, buff=0.5)  # safe bottom

# For custom resolutions
config.pixel_height = 1920  # portrait
config.pixel_width = 1080
# Frame dimensions change accordingly
```

### 11.3 Portrait mode coordinate differences

**Root cause:** In portrait (9:16), the frame is taller than wide. X bounds shrink, Y bounds expand.

**Fix:**
```python
# For portrait mode (1080x1920):
# x range: approximately -4.0 to 4.0
# y range: approximately -7.11 to 7.11
# Axes should be smaller
axes = Axes(x_range=[-3, 3, 1], y_range=[-5, 5, 1],
            x_length=5, y_length=8)
```

### 11.4 --resolution flag format

**Usage:**
```bash
manim -qh scene.py SceneName --resolution 1920,1080     # landscape
manim -qh scene.py SceneName --resolution 1080,1920     # portrait
# Format: width,height (no spaces)
```

---

## 12. Common Script Generation Errors

### 12.1 Overlapping mobjects

**Symptom:** Objects stacked on top of each other, unreadable.

**Root cause:** Multiple objects placed at ORIGIN or same position without arrangement.

**Fix:**
```python
# BAD
title = Text("Title").move_to(ORIGIN)
formula = MathTex(r"E=mc^2").move_to(ORIGIN)
graph_label = Text("Graph").move_to(ORIGIN)

# GOOD - use zones
title = Text("Title").to_edge(UP, buff=0.3)
formula = MathTex(r"E=mc^2").shift(UP * 1.8)
axes = Axes(...).shift(DOWN * 0.4)
caption = Text("Caption").to_edge(DOWN, buff=0.4)
```

### 12.2 Off-screen positioning

**Symptom:** Objects invisible or partially cut off.

**Root cause:** Using large shift values or positioning beyond frame bounds.

**Fix:**
```python
# BAD
text.shift(UP * 6)  # off top of screen (max y ~ 4.0)
text.shift(RIGHT * 10)  # off right of screen (max x ~ 7.11)

# GOOD
text.to_edge(UP, buff=0.3)  # safe
text.to_edge(RIGHT, buff=0.3)  # safe
```

### 12.3 Empty animations / black frames

**Symptom:** Video has frames with nothing visible.

**Root causes:**
1. Forgetting to add objects to scene before or during animation
2. FadeOut of everything with no FadeIn following
3. Using `self.wait()` when nothing is on screen
4. Animation run_time of 0

**Fix:**
```python
# Ensure something is always visible
self.play(FadeOut(old_content), FadeIn(new_content))  # simultaneous
# NOT:
self.play(FadeOut(old_content))
self.wait(2)  # BLACK FRAME for 2 seconds
self.play(FadeIn(new_content))
```

### 12.4 Stale objects not cleaned up

**Symptom:** Previous section's objects overlap with new section.

**Fix:**
```python
# Always clean up before building next section
self.play(FadeOut(VGroup(axes, graph, labels, formula, caption)), run_time=0.5)
# Then build next section
```

### 12.5 Text too long / overflowing

**Symptom:** Text goes off screen edges.

**Fix:**
```python
# BAD
text = Text("This is a very long sentence that will definitely go off the screen edges")

# GOOD - limit width or font size
text = Text("This is a very long sentence...",
            font_size=20).scale_to_fit_width(12)

# Or use line breaks
text = Text("This is a very long\nsentence that wraps\nproperly", font_size=24)
```

### 12.6 MathTex with text mode issues

**Root cause:** Putting plain text inside `MathTex` without `\text{}`.

**Fix:**
```python
# BAD - renders weirdly in math mode
MathTex("Gradient Descent")  # letters will be italic, no spaces

# GOOD
MathTex(r"\text{Gradient Descent}")
# Or use Tex instead
Tex("Gradient Descent")
# Or use Text for non-math
Text("Gradient Descent")
```

---

## 13. Voiceover / Audio Sync Issues

### 13.1 manim-voiceover not installed

**Exact error:**
```
ModuleNotFoundError: No module named 'manim_voiceover'
```

**Fix:**
```bash
pip install manim-voiceover
pip install "manim-voiceover[elevenlabs]"
```

### 13.2 ElevenLabs API key invalid

**Exact error:**
```
elevenlabs.api.error.AuthenticationError: ...
```
or:
```
ValueError: ELEVENLABS_API_KEY not set
```

**Fix:** Set valid API key in `.env`:
```
ELEVENLABS_API_KEY=your_key_here
```

### 13.3 Audio longer than animations

**Symptom:** Voiceover continues after animations finish, leaving static frame.

**Fix:**
```python
with self.voiceover(text="Long narration...") as tracker:
    self.play(Create(axes), run_time=1)
    self.play(Create(graph), run_time=2)
    # IMPORTANT: wait for remaining audio
    remaining = tracker.get_remaining_duration(buff=-0.3)
    if remaining > 0:
        self.wait(remaining)
```

### 13.4 Audio shorter than animations

**Symptom:** Animations play in silence after voiceover ends.

**Fix:** Keep animation run_times shorter, or split into multiple voiceover blocks.

### 13.5 Voiceover with statement missing tracker

**Exact error:** Varies -- usually audio/animation desync.

**Fix:**
```python
# BAD
with self.voiceover(text="Hello"):  # no 'as tracker'
    self.play(Write(text))
    # can't sync timing

# GOOD
with self.voiceover(text="Hello") as tracker:
    self.play(Write(text))
    remaining = tracker.get_remaining_duration(buff=-0.3)
    if remaining > 0:
        self.wait(remaining)
```

---

## 14. Performance Issues

### 14.1 Too many mobjects

**Symptom:** Render takes minutes/hours, or runs out of memory.

**Root causes and fixes:**

```python
# BAD - 10000 dots
dots = VGroup(*[Dot(point=np.array([x/100, y/100, 0]))
                for x in range(-100, 100) for y in range(-50, 50)])

# GOOD - reduce count or use point cloud
dots = VGroup(*[Dot(point=np.array([x/10, y/10, 0]))
                for x in range(-10, 10) for y in range(-5, 5)])

# Or use DotCloud for many points (much faster)
from manim import DotCloud
cloud = DotCloud(points)
```

### 14.2 Too many TeX compilations

**Root cause:** Each unique `MathTex`/`Tex` string triggers a LaTeX compilation.

**Fix:**
```python
# BAD - compiles LaTeX 100 times
for i in range(100):
    self.play(Write(MathTex(f"x = {i}")))

# GOOD - use DecimalNumber for changing values
num = DecimalNumber(0)
self.play(ChangeDecimalToValue(num, 100), run_time=5)
```

### 14.3 Very long videos

**Root cause:** Single scene trying to render 10+ minutes of content.

**Fix:** Split into multiple scenes or keep under 2-3 minutes.

### 14.4 Large image mobjects

**Root cause:** High-resolution images embedded as `ImageMobject`.

**Fix:** Resize images before use, or use lower resolution.

### 14.5 Riemann rectangles / many sub-mobjects

**Fix:**
```python
# BAD
rects = axes.get_riemann_rectangles(graph, dx=0.001)  # 10000+ rectangles

# GOOD
rects = axes.get_riemann_rectangles(graph, dx=0.1)  # 100 rectangles
```

### 14.6 Memory issues with ValueTracker + always_redraw

**Root cause:** `always_redraw` recreates the mobject every frame. If the creation is expensive, this causes lag.

**Fix:**
```python
# BAD - expensive recreation
graph = always_redraw(lambda: axes.plot(
    lambda x: some_expensive_function(x, param.get_value()),
    x_range=[-10, 10, 0.001]
))

# GOOD - simpler recreation or use become()
graph = always_redraw(lambda: axes.plot(
    lambda x: param.get_value() * x**2,
    x_range=[-5, 5, 0.1]  # coarser step
))
```

---

## 15. LaTeX Command Compatibility

### Commands that WORK in MathTex (via default amsmath template)

```python
# Basic math
MathTex(r"\frac{a}{b}")           # fractions
MathTex(r"\sqrt{x}")              # square root
MathTex(r"\sqrt[3]{x}")           # nth root
MathTex(r"\int_0^1 f(x)\,dx")    # integrals
MathTex(r"\sum_{i=0}^n x_i")     # summations
MathTex(r"\prod_{i=1}^n x_i")    # products
MathTex(r"\lim_{x\to 0}")        # limits
MathTex(r"\partial f / \partial x")  # partial derivatives
MathTex(r"\nabla f")              # nabla
MathTex(r"\vec{v}")               # vector arrow
MathTex(r"\hat{x}")               # hat accent
MathTex(r"\bar{x}")               # bar accent
MathTex(r"\dot{x}")               # dot accent
MathTex(r"\ddot{x}")              # double dot
MathTex(r"\tilde{x}")             # tilde
MathTex(r"\mathbb{R}")            # blackboard bold
MathTex(r"\mathcal{L}")           # calligraphic
MathTex(r"\mathbf{x}")            # bold math
MathTex(r"\mathrm{d}x")           # roman in math
MathTex(r"\text{hello}")          # text in math (amsmath)
MathTex(r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}")  # matrices
MathTex(r"\begin{bmatrix} 1 \\ 2 \end{bmatrix}")
MathTex(r"\begin{cases} x & x>0 \\ 0 & x\le 0 \end{cases}")
MathTex(r"\binom{n}{k}")          # binomial
MathTex(r"\forall x \in \mathbb{R}")
MathTex(r"\exists x")
MathTex(r"\alpha, \beta, \gamma, \delta, \epsilon")
MathTex(r"\theta, \lambda, \mu, \sigma, \omega")
MathTex(r"\Gamma, \Delta, \Theta, \Lambda, \Sigma, \Omega")
MathTex(r"\infty")
MathTex(r"\approx, \neq, \leq, \geq")
MathTex(r"\subset, \supset, \in, \cup, \cap")
MathTex(r"\rightarrow, \leftarrow, \Rightarrow, \Leftarrow")
MathTex(r"\cdot, \times, \div, \pm")
MathTex(r"\underbrace{x+y}_{z}")
MathTex(r"\overbrace{a+b}^{n}")
MathTex(r"\overset{def}{=}")      # from amsmath
MathTex(r"\underset{x}{min}")     # from amsmath
MathTex(r"\xrightarrow{f}")       # from amsmath
MathTex(r"\boxed{E=mc^2}")        # from amsmath
```

### Commands that DO NOT WORK without extra packages

```python
# BAD - requires cancel package
MathTex(r"\cancel{x}")
# FIX:
template = TexTemplate()
template.add_to_preamble(r"\usepackage{cancel}")
MathTex(r"\cancel{x}", tex_template=template)

# BAD - requires mathrsfs
MathTex(r"\mathscr{L}")
# FIX:
template = TexTemplate()
template.add_to_preamble(r"\usepackage{mathrsfs}")
MathTex(r"\mathscr{L}", tex_template=template)

# BAD - requires physics
MathTex(r"\bra{\psi}")
MathTex(r"\ket{\psi}")
MathTex(r"\braket{\phi|\psi}")
# FIX:
template = TexTemplate()
template.add_to_preamble(r"\usepackage{physics}")
MathTex(r"\bra{\psi}", tex_template=template)

# BAD - requires xcolor with dvipsnames
MathTex(r"\color{BurntOrange}{x}")  # may not work

# BAD - requires tikz
MathTex(r"\tikz{...}")  # absolutely won't work in MathTex

# BAD - not a real command
MathTex(r"\R")     # Use \mathbb{R}
MathTex(r"\N")     # Use \mathbb{N}
MathTex(r"\Z")     # Use \mathbb{Z}
MathTex(r"\Q")     # Use \mathbb{Q}
MathTex(r"\C")     # Use \mathbb{C}
```

### Common LaTeX ESCAPING issues

```python
# BAD - Python eats the backslashes
MathTex("\frac{1}{2}")      # \f = form feed!
MathTex("\theta")            # \t = tab!
MathTex("\nabla")            # \n = newline!
MathTex("\alpha")            # \a = bell!

# GOOD - always use raw strings
MathTex(r"\frac{1}{2}")
MathTex(r"\theta")
MathTex(r"\nabla")
MathTex(r"\alpha")
```

### MathTex multi-part strings for TransformMatchingTex

```python
# For TransformMatchingTex, split into parts:
eq1 = MathTex("a", "x^2", "+", "b", "x", "+", "c", "=", "0")
eq2 = MathTex("x", "=", r"\frac{-b \pm \sqrt{b^2-4ac}}{2a}")

self.play(TransformMatchingTex(eq1, eq2))
# Parts with matching TeX strings will transform into each other
```

### Tex vs MathTex

```python
# Tex - for mixed text+math (wraps in document environment)
Tex(r"The value of $\pi$ is approximately 3.14")
Tex(r"Hello \textbf{World}")

# MathTex - for pure math (wraps in align* environment by default)
MathTex(r"E = mc^2")
MathTex(r"\int_0^\infty e^{-x}\,dx = 1")

# Common mistake: putting $ inside MathTex
# BAD
MathTex(r"$E = mc^2$")  # Double math mode!

# GOOD
MathTex(r"E = mc^2")
```

---

## 16. Color and Styling Errors

### 16.1 Invalid color values

**Exact error:**
```
ValueError: Invalid color: ...
```

**Root cause:** Passing invalid color strings.

**Fix:**
```python
# BAD
Circle(color="red")        # lowercase doesn't work
Circle(color="0xFF0000")   # wrong format

# GOOD - Manim CE color constants
Circle(color=RED)
Circle(color=BLUE)
Circle(color="#FF0000")    # hex strings work
Circle(color=ManimColor.from_hex("#FF0000"))

# Available color constants (partial list):
# WHITE, BLACK, GREY, RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, PINK
# TEAL, GOLD, MAROON
# Shades: BLUE_A, BLUE_B, BLUE_C, BLUE_D, BLUE_E
# (A=lightest, E=darkest, same for other colors)
# GREY_A through GREY_E
# PURE_RED, PURE_GREEN, PURE_BLUE
```

### 16.2 set_color on non-existent submobjects

**Root cause:** Trying to color-index into a mobject with no submobjects.

**Fix:**
```python
# BAD
text = Text("Hello")
text[0].set_color(RED)   # Might fail depending on text rendering

# GOOD
MathTex("a", "+", "b")[0].set_color(RED)  # 'a' in red
MathTex("a", "+", "b")[2].set_color(BLUE)  # 'b' in blue
```

### 16.3 Opacity issues

```python
# Set fill opacity
rect = Rectangle(fill_opacity=0.5, fill_color=BLUE)

# Set stroke opacity
line = Line(stroke_opacity=0.3)

# Set overall opacity
mob.set_opacity(0.5)
```

---

## 17. Camera and 3D Errors

### 17.1 move_camera on non-ThreeDScene

**Exact error:**
```
AttributeError: 'Scene' object has no attribute 'move_camera'
```

**Root cause:** `move_camera` is only available on `ThreeDScene`.

**Fix:**
```python
# BAD
class MyScene(Scene):
    def construct(self):
        self.move_camera(phi=60*DEGREES)  # ERROR

# GOOD - use ThreeDScene
class MyScene(ThreeDScene):
    def construct(self):
        self.move_camera(phi=60*DEGREES)

# Or remove 3D camera calls entirely for 2D scenes
```

**Sanitization regex:**
```python
code = re.sub(r'^\s*self\.move_camera\(.*?\)\s*$', '', code, flags=re.MULTILINE)
code = re.sub(r'^\s*self\.set_camera_orientation\(.*?\)\s*$', '', code, flags=re.MULTILINE)
```

### 17.2 set_camera_orientation on non-ThreeDScene

**Exact error:**
```
AttributeError: 'Scene' object has no attribute 'set_camera_orientation'
```

**Fix:** Same as above -- use ThreeDScene or remove the call.

### 17.3 ThreeDAxes in 2D Scene

**Root cause:** Using `ThreeDAxes` without `ThreeDScene` produces a flat 2D projection with no 3D perspective.

**Fix:**
```python
# For 2D, use Axes
axes = Axes(x_range=[-5, 5], y_range=[-3, 3])

# For 3D, use ThreeDScene + ThreeDAxes
class My3DScene(ThreeDScene):
    def construct(self):
        axes = ThreeDAxes()
        self.set_camera_orientation(phi=75*DEGREES, theta=-45*DEGREES)
```

### 17.4 Surface in 2D Scene

**Root cause:** `Surface` objects won't render properly in a 2D Scene.

**Fix:** Use `ThreeDScene` with proper camera orientation.

### 17.5 self.camera.background_color on ThreeDScene

**Root cause:** In ThreeDScene, setting background color works differently.

**Fix:**
```python
class MyScene(ThreeDScene):
    def construct(self):
        self.camera.background_color = "#000000"  # This works in CE
```

---

## 18. Updater and ValueTracker Errors

### 18.1 ValueTracker lambda closure bug

**Exact error:** All animated objects snap to final value instead of smoothly animating.

**Root cause:** Python closure captures variable by reference. In a loop, all lambdas reference the same variable.

**Fix:**
```python
# BAD - closure bug
trackers = []
for i in range(5):
    t = ValueTracker(0)
    dot = always_redraw(lambda: Dot(axes.c2p(t.get_value(), i)))  # i is always 4!
    trackers.append(t)

# GOOD - capture value at creation time
for i in range(5):
    t = ValueTracker(0)
    dot = always_redraw(lambda i=i, t=t: Dot(axes.c2p(t.get_value(), i)))
```

### 18.2 always_redraw with side effects

**Root cause:** `always_redraw` creates a new mobject every frame. If the lambda has side effects (appending to lists, printing, etc.), they happen every frame.

**Fix:** Keep always_redraw lambdas pure -- they should only create and return a mobject.

### 18.3 Updater removed prematurely

**Root cause:** Calling `FadeOut` on a mobject with an updater removes the mobject but the updater may cause errors.

**Fix:**
```python
# Remove updater before fading out
mob.clear_updaters()
self.play(FadeOut(mob))
```

### 18.4 ValueTracker.set_value() vs animate.set_value()

```python
# Instant (no animation):
tracker.set_value(5)

# Animated (smooth transition):
self.play(tracker.animate.set_value(5), run_time=3)
```

### 18.5 Recursive updater errors

**Exact error:**
```
RecursionError: maximum recursion depth exceeded
```

**Root cause:** Updater references mobject that triggers another update.

**Fix:** Don't create circular update dependencies.

---

## 19. File and Rendering Pipeline Errors

### 19.1 "No scene class found" / wrong class name

**Exact error:**
```
ValueError: No scene class found matching ...
```

**Root cause:** The scene class name passed to `manim` CLI does not match any class in the file.

**Fix:**
```bash
# The class name must match exactly
manim -qh scene.py MyScene  # must match `class MyScene(Scene):`
```

### 19.2 ffmpeg not found

**Exact error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**Root cause:** ffmpeg is not installed.

**Fix:**
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`

### 19.3 Render timeout

**Root cause:** Scene is too complex or has infinite loops.

**Fix:** Set timeout, simplify scene, check for infinite `while` loops.

### 19.4 Output file location confusion

Manim CE outputs to `media/videos/<scene_file>/<quality>/` by default.

**Fix:**
```bash
manim -qh scene.py MyScene --media_dir ./output
```

### 19.5 Quality flags

```bash
-ql  # 480p (low)
-qm  # 720p (medium)
-qh  # 1080p (high)
-qp  # 1440p (production)
-qk  # 2160p (4K)
```

### 19.6 Partial movie files issue

**Root cause:** Manim creates partial movie files for each `self.play()` call, then concatenates. If rendering fails midway, partial files remain.

**Fix:** Delete the `partial_movie_files` directory and re-render.

### 19.7 Permission denied on media directory

**Root cause:** No write permission to output directory.

**Fix:** Change output directory or fix permissions:
```bash
manim -qh scene.py MyScene --media_dir /tmp/manim_output
```

---

## 20. Complete Sanitization Regex Reference

Below is the comprehensive sanitization function that fixes ALL known AI-generation errors. This should be applied to every generated script before rendering.

```python
import re

def sanitize_manim_script(code: str) -> str:
    """Fix ALL common Manim CE errors in AI-generated scripts.

    Covers: manimlib->CE renames, domain errors, empty strings,
    3D in 2D, lambda closures, and more.
    """

    # ─── IMPORT FIXES ───────────────────────────────────────

    # manimlib -> manim
    code = re.sub(r'from\s+manimlib\.imports\s+import\s+\*', 'from manim import *', code)
    code = re.sub(r'from\s+manimlib\s+import\s+\*', 'from manim import *', code)

    # ─── ANIMATION RENAMES ──────────────────────────────────

    # ShowCreation -> Create
    code = re.sub(r'\bShowCreation\b', 'Create', code)

    # TextMobject -> Tex
    code = re.sub(r'\bTextMobject\b', 'Tex', code)

    # TexMobject -> MathTex
    code = re.sub(r'\bTexMobject\b', 'MathTex', code)

    # ParametricSurface -> Surface
    code = re.sub(r'\bParametricSurface\b', 'Surface', code)

    # Directional fades (approximate -- may need manual review)
    code = re.sub(r'\bFadeInFromDown\b', 'FadeIn', code)
    code = re.sub(r'\bFadeInFromLarge\b', 'FadeIn', code)
    code = re.sub(r'\bFadeOutAndShift\b', 'FadeOut', code)
    code = re.sub(r'\bFadeOutAndShiftDown\b', 'FadeOut', code)
    code = re.sub(r'\bFadeInFrom\b', 'FadeIn', code)
    code = re.sub(r'\bFadeInFromPoint\b', 'FadeIn', code)
    code = re.sub(r'\bShowPassingFlashAround\b', 'Circumscribe', code)

    # ─── METHOD RENAMES ─────────────────────────────────────

    # get_graph -> plot (on Axes)
    code = re.sub(r'\.get_graph\(', '.plot(', code)

    # ─── LAMBDA DOMAIN FIXES ────────────────────────────────

    # max(0, x) -> np.maximum(0, x) in lambdas
    code = re.sub(
        r'lambda\s+(\w+)\s*:\s*max\(0,\s*\1\)',
        r'lambda \1: np.maximum(0, \1)',
        code
    )
    code = re.sub(
        r'lambda\s+(\w+)\s*:\s*max\((\w+),\s*0\)',
        r'lambda \1: np.maximum(\2, 0)',
        code
    )

    # min(x, val) -> np.minimum(x, val) in lambdas
    code = re.sub(
        r'lambda\s+(\w+)\s*:\s*min\((\w+),\s*(\w+)\)',
        r'lambda \1: np.minimum(\2, \3)',
        code
    )

    # abs(x) -> np.abs(x) in lambdas (for safety)
    code = re.sub(
        r'lambda\s+(\w+)\s*:(.*)(?<!\w)abs\((\w+)\)',
        r'lambda \1:\2np.abs(\3)',
        code
    )

    # ─── 3D IN 2D FIXES ────────────────────────────────────

    # Remove move_camera calls (only work in ThreeDScene)
    code = re.sub(r'^\s*self\.move_camera\(.*?\)\s*$', '', code, flags=re.MULTILINE)

    # Remove set_camera_orientation calls
    code = re.sub(r'^\s*self\.set_camera_orientation\(.*?\)\s*$', '', code, flags=re.MULTILINE)

    # ─── EMPTY STRING FIXES ─────────────────────────────────

    # Empty Text constructors
    code = re.sub(r'Text\(\s*""\s*\)', 'Text(" ")', code)
    code = re.sub(r"Text\(\s*''\s*\)", "Text(' ')", code)

    # Empty MathTex/Tex constructors
    code = re.sub(r'MathTex\(\s*""\s*\)', r'MathTex(r"\\quad")', code)
    code = re.sub(r"MathTex\(\s*''\s*\)", r"MathTex(r'\\quad')", code)
    code = re.sub(r'Tex\(\s*""\s*\)', r'Tex(r"\\quad")', code)
    code = re.sub(r"Tex\(\s*''\s*\)", r"Tex(r'\\quad')", code)

    # ─── LATEX ESCAPING FIXES ───────────────────────────────

    # Detect non-raw LaTeX strings and warn (can't auto-fix reliably)
    # This is a detection pattern, not a replacement:
    # re.findall(r'MathTex\(\s*"(?!r")\\', code)

    # ─── NEGATIVE RUN_TIME PREVENTION ───────────────────────

    # Ensure wait calls check for positive duration
    code = re.sub(
        r'(\s*)self\.wait\(remaining\)',
        r'\1if remaining > 0:\n\1    self.wait(remaining)',
        code
    )

    # ─── GRAPHSCENE REMOVAL ─────────────────────────────────

    # Replace GraphScene inheritance
    code = re.sub(r'\(GraphScene\)', '(Scene)', code)

    # Remove setup_axes calls
    code = re.sub(r'^\s*self\.setup_axes\(\)\s*$', '', code, flags=re.MULTILINE)

    # ─── PLAY METHOD FIXES ──────────────────────────────────

    # Remove self.play() calls with no arguments (would raise ValueError)
    code = re.sub(r'^\s*self\.play\(\s*\)\s*$', '', code, flags=re.MULTILINE)

    # ─── CONFIG DICT REMOVAL ────────────────────────────────

    # Remove CONFIG = {} class variables (manimlib pattern)
    code = re.sub(r'^\s*CONFIG\s*=\s*\{[^}]*\}\s*$', '', code, flags=re.MULTILINE | re.DOTALL)

    # ─── SCENE.DITHER -> SCENE.WAIT ────────────────────────

    code = re.sub(r'self\.dither\(', 'self.wait(', code)

    return code
```

---

## ADDITIONAL COMMON ERRORS BY CATEGORY

### A. Manim CLI / Config Errors

| Error | Cause | Fix |
|---|---|---|
| `TypeError: 'NoneType' object is not iterable` on startup | Corrupted config file | Delete `~/.config/manim/manim.cfg` |
| `FileNotFoundError: media directory` | Custom media_dir doesn't exist | Create the directory first |
| `PermissionError` | No write permission | Use `--media_dir /tmp/manim` |

### B. OpenGL Renderer Errors

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'moderngl'` | OpenGL renderer not installed | `pip install manim[opengl]` |
| `RuntimeError: OpenGL context creation failed` | No display server / headless | Use Cairo renderer (default) or `xvfb-run` |

### C. SVG Parsing Errors

| Error | Cause | Fix |
|---|---|---|
| `ValueError: SVG parse error` | Invalid SVG file | Verify SVG validity |
| `FileNotFoundError: SVG file not found` | Wrong path to SVG | Use absolute path |

### D. Table Mobject Errors

| Error | Cause | Fix |
|---|---|---|
| `ValueError: Number of entries in row X does not match` | Unequal row lengths | Pad shorter rows |
| Empty cells cause errors | Empty string in table | Use `" "` for empty cells |

### E. Boolean Operations Errors

| Error | Cause | Fix |
|---|---|---|
| `TypeError: Union only works with VMobjects` | Non-VMobject input | Use only VMobjects |
| Boolean op produces empty result | Shapes don't overlap | Verify intersection |

### F. NumberLine Errors

| Error | Cause | Fix |
|---|---|---|
| Ticks too dense / slow render | step_size too small | Increase step_size |
| Labels overlapping | Too many labels | Use `numbers_to_include` to select specific labels |

---

## QUICK REFERENCE: Most Common AI-Generation Errors

The most frequent errors when Claude or other LLMs generate Manim scripts, in order of frequency:

1. **`ShowCreation` instead of `Create`** -- manimlib name
2. **`get_graph()` instead of `plot()`** -- manimlib method name
3. **`max(0, x)` in lambdas** -- should be `np.maximum(0, x)`
4. **Empty string `Text("")`** -- causes crash
5. **Non-raw LaTeX strings** -- `"\frac"` instead of `r"\frac"`
6. **move_camera in 2D Scene** -- only works in ThreeDScene
7. **Overlapping mobjects** -- everything at ORIGIN
8. **Missing cleanup between sections** -- stale objects remain
9. **Negative run_time from tracker** -- need `if remaining > 0` guard
10. **GraphScene usage** -- removed in CE, use Axes directly
11. **TextMobject/TexMobject** -- renamed to Tex/MathTex
12. **FadeInFromDown etc.** -- removed, use FadeIn(shift=UP)
13. **Objects off-screen** -- shift values too large
14. **Black frames** -- gap between FadeOut and FadeIn
15. **$ inside MathTex** -- double math mode
16. **Plain text in MathTex** -- missing `\text{}`
17. **Missing numpy import** -- `np.maximum` needs numpy
18. **Axes with no step size** -- defaults may be wrong
19. **VGroup of non-Mobjects** -- TypeError
20. **self.play() with no args** -- ValueError
