"""
Shared styles, colors, helpers, and base scene for Octoflash animations.
Adapted from context-zero-manin-demo/aiintuition/styles.py.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# manim_voiceover.services.elevenlabs reads os.environ["ELEVEN_API_KEY"] at
# IMPORT TIME and prompts interactively if it's missing (EOFError in non-tty
# contexts like the Manim subprocess). Hydrate the env var from .env.dev / .env.dev.local
# BEFORE we trigger that import. In dev the .env.dev.local file matters; in the
# Manim subprocess, the parent renderer also explicitly forwards the key via
# _build_env() — both paths guarantee it's set before any import side-effects.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for _candidate in (".env.dev.local", ".env.dev.dev", ".env.dev"):
    _path = _PROJECT_ROOT / _candidate
    if _path.exists():
        load_dotenv(_path, override=False)

from manim import (
    Scene, VGroup, Text, RoundedRectangle, Code,
    Circle, AnnularSector, Sector, Annulus,
    FadeIn, FadeOut, Write,
    MathTex, Tex,
    UP, DOWN, LEFT, RIGHT, ORIGIN, UR, UL, DR, DL,
    PI, TAU,
    config, ThreeDScene,
)
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.elevenlabs import ElevenLabsService

# ── Brand Colors ─────────────────────────────────────────────────────────────
BG_COLOR       = "#000000"   # pitch black background
CODE_BG        = "#0a0a0a"
ACCENT_BLUE    = "#4fc3f7"
ACCENT_ORANGE  = "#ff9800"
ACCENT_GREEN   = "#66bb6a"
ACCENT_RED     = "#ef5350"
ACCENT_PURPLE  = "#ab47bc"
ACCENT_YELLOW  = "#ffee58"
ACCENT_CYAN    = "#26c6da"
ACCENT_PINK    = "#ec407a"
TEXT_PRIMARY    = "#ffffff"   # bright white for all general text
TEXT_SECONDARY  = "#e0e0e0"  # near-white, readable on black
TEXT_DIM        = "#9e9e9e"  # muted but still visible on black

# ── Font Sizes ───────────────────────────────────────────────────────────────
TITLE_SIZE     = 38   # bold section titles at top (fits ~40 chars per line)
SUBTITLE_SIZE  = 30
BODY_SIZE      = 24
LABEL_SIZE     = 20
CODE_FONT_SIZE = 20


# ── ElevenLabs Voice Config ──────────────────────────────────────────────────
ELEVENLABS_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel — British male (default)
ELEVENLABS_MODEL    = "eleven_multilingual_v2"


def get_speech_service():
    """Return configured ElevenLabs service.

    Voice is selected by the OCTOFLASH_VOICE_ID env var (set by renderer.py from
    the video's voice_id field). Falls back to ELEVENLABS_VOICE_ID if unset.

    Patches the elevenlabs SDK's voices() call to avoid the /v1/voices endpoint,
    which requires the voices_read permission that restricted API keys lack.
    """
    from elevenlabs.api.voice import Voice
    import manim_voiceover.services.elevenlabs as el_service

    voice_id = os.environ.get("OCTOFLASH_VOICE_ID") or ELEVENLABS_VOICE_ID

    # Create a fake voice object — bypass the voices listing API call
    fake_voice = Voice(voice_id=voice_id, name="Selected")
    original_voices = el_service.voices

    # Patch at the module level where it's actually called
    el_service.voices = lambda: [fake_voice]

    try:
        service = ElevenLabsService(
            voice_id=voice_id,
            model=ELEVENLABS_MODEL,
            transcription_model=None,
        )
    finally:
        el_service.voices = original_voices

    return service


# ── Octoflash Logo (D-shape inside a ring) ──────────────────────────────────
def make_octoflash_logo(radius: float = 0.22) -> VGroup:
    """Build the Octoflash brand mark: thick white ring with a white half-disc
    on the LEFT hemisphere.

    Outer circle is outlined in white; left hemisphere is filled solid; right
    hemisphere is hollow. From the viewer's perspective the bright half is on
    the LEFT.
    """
    ring_thickness = radius * 0.25
    inner_gap = radius * 0.4

    ring = Annulus(
        inner_radius=radius - ring_thickness,
        outer_radius=radius,
        color=TEXT_PRIMARY,
        fill_opacity=1.0,
        stroke_width=0,
    )

    # Half-disc on the LEFT hemisphere. start_angle=PI/2 (12 o'clock) sweeping
    # counter-clockwise by PI fills the left side (12 → 9 → 6).
    d_radius = radius - ring_thickness - inner_gap
    d_shape = Sector(
        radius=d_radius,
        angle=PI,
        start_angle=3 * PI / 2,
        color=TEXT_PRIMARY,
        fill_opacity=1.0,
        stroke_width=0,
    )
    return VGroup(ring, d_shape)


# Backwards-compat alias — existing generated Manim scripts call this name.
# Removed in a future version once all stored scripts are regenerated.
make_contextzero_logo = make_octoflash_logo


def make_brand_watermark() -> VGroup:
    """
    Brand watermark — currently disabled (returns empty VGroup).

    The three base scene classes still call this and `.add()` the result, so
    keeping it as a no-op is the lowest-risk way to remove the watermark
    without touching every caller or invalidating the script-generator
    prompts (which tell Claude to leave headroom above titles — extra room
    is harmless on its own).
    """
    return VGroup()


# Manim CE: classes added in 0.18+. Older versions may not have all of these,
# so try the imports defensively.
try:
    from manim import Tex as _Tex
except ImportError:
    _Tex = None


def _apply_brand_defaults():
    """Lock MathTex/Tex defaults so even sloppy generated code looks branded.

    set_default works reliably for MathTex/Tex but NOT for Text in Manim 0.18
    (Text builds via Pango before the default takes effect, so color stays
    black). For Text consistency, use the `Title` / `BodyText` / `Caption`
    wrapper classes below — those force the right color + size in __init__.

    NB: we do NOT override `font` on MathTex/Tex either. Manim's Text/Tex
    constructor concatenates `self.font` as a string in `_text2hash`, so
    passing `font=None` at the default level crashes instantiation.
    """
    MathTex.set_default(color=TEXT_PRIMARY, font_size=BODY_SIZE)
    if Tex is not None:
        Tex.set_default(color=TEXT_PRIMARY, font_size=BODY_SIZE)


# ── Layer 3: branded wrapper classes — generated code MUST use these ───────────
# Subclassing Text instead of relying on `Text.set_default(color=...)` because
# that doesn't take effect in 0.18 (see _apply_brand_defaults note above).
# `kwargs.setdefault(...)` means explicit overrides in user code still win.


def _make_text_subclass(default_font_size: int, default_color: str, default_weight: str | None = None):
    """Build a Text subclass that *forces* color via post-init set_color().

    Why: in Manim 0.18, passing `color=...` to `Text.__init__` doesn't reliably
    propagate through the Pango render pipeline — `t.color` reads as #000000
    even though we passed white. `set_color()` after construction does
    propagate. Calling pattern: pop the user's color (or fall back to the
    branded default), pass everything else to Text, then force the color.
    Explicit `color=...` in user code still wins because we honor it.
    """
    class _Branded(Text):
        def __init__(self, text, **kwargs):
            target_color = kwargs.pop("color", default_color)
            kwargs.setdefault("font_size", default_font_size)
            if default_weight is not None:
                kwargs.setdefault("weight", default_weight)
            super().__init__(text, **kwargs)
            self.set_color(target_color)
    return _Branded


# Layer 3 wrappers — generated code MUST use these instead of raw Text().
Title = _make_text_subclass(TITLE_SIZE, TEXT_PRIMARY, default_weight="BOLD")
Title.__name__ = "Title"
Title.__doc__ = "Top-of-frame title. White, bold, TITLE_SIZE. Caller positions with .to_edge(UP, buff=0.7)."

BodyText = _make_text_subclass(BODY_SIZE, TEXT_PRIMARY)
BodyText.__name__ = "BodyText"
BodyText.__doc__ = "Default body text. White, BODY_SIZE."

Caption = _make_text_subclass(LABEL_SIZE, TEXT_SECONDARY)
Caption.__name__ = "Caption"
Caption.__doc__ = "Subtitle / lower-third caption. Muted, LABEL_SIZE. Caller positions with .to_edge(DOWN, buff=0.4)."


class MathExpr(MathTex):
    """Branded MathTex. White by default, slightly larger than BODY_SIZE for legibility."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("font_size", 40)
        kwargs.setdefault("color", TEXT_PRIMARY)
        super().__init__(*args, **kwargs)


# ── Base Scene (2D, no voiceover) ────────────────────────────────────────────
class OctoflashSceneNoVoice(Scene):
    """Plain 2D scene with dark background + brand watermark (no voiceover)."""

    def setup(self):
        super().setup()
        self.camera.background_color = BG_COLOR
        _apply_brand_defaults()
        self._brand_watermark = make_brand_watermark()
        self._brand_watermark.set_z_index(1000)
        self.add(self._brand_watermark)


# ── Base Scene (2D) ──────────────────────────────────────────────────────────
class OctoflashScene(VoiceoverScene):
    """Base 2D scene with dark background + ElevenLabs voiceover + brand watermark."""

    def setup(self):
        super().setup()
        self.camera.background_color = BG_COLOR
        _apply_brand_defaults()
        self.set_speech_service(get_speech_service())
        # Persistent brand watermark — added before any animation so it's always on top
        self._brand_watermark = make_brand_watermark()
        self._brand_watermark.set_z_index(1000)
        self.add(self._brand_watermark)


# ── Base Scene (3D) ──────────────────────────────────────────────────────────
class Octoflash3DScene(ThreeDScene, VoiceoverScene):
    """Base 3D scene with dark background + ElevenLabs voiceover + brand watermark."""

    def setup(self):
        ThreeDScene.setup(self)
        VoiceoverScene.setup(self)
        self.camera.background_color = BG_COLOR
        _apply_brand_defaults()
        self.set_speech_service(get_speech_service())
        self._brand_watermark = make_brand_watermark()
        self._brand_watermark.set_z_index(1000)
        try:
            self.add_fixed_in_frame_mobjects(self._brand_watermark)
        except Exception:
            self.add(self._brand_watermark)


# ── Helper: Title Card ───────────────────────────────────────────────────────
def make_title_card(title: str, subtitle: str = "") -> VGroup:
    """Branded intro card with title and optional subtitle."""
    title_text = Text(
        title,
        font_size=TITLE_SIZE,
        color=TEXT_PRIMARY,
        weight="BOLD",
    )

    if subtitle:
        sub_text = Text(
            subtitle,
            font_size=SUBTITLE_SIZE,
            color=ACCENT_CYAN,
        ).next_to(title_text, DOWN, buff=0.4)
        return VGroup(title_text, sub_text).move_to(ORIGIN)

    return VGroup(title_text).move_to(ORIGIN)


# ── Helper: Rounded Rect Cell ──────────────────────────────────────────────
def make_cell(
    label: str,
    width: float = 0.8,
    height: float = 0.6,
    color: str = ACCENT_BLUE,
    font_size: int = LABEL_SIZE,
) -> VGroup:
    """Single rounded-rect cell with centered label."""
    rect = RoundedRectangle(
        corner_radius=0.08,
        width=width,
        height=height,
        fill_color=color,
        fill_opacity=0.3,
        stroke_color=color,
        stroke_width=2,
    )
    txt = Text(str(label), font_size=font_size, color=TEXT_PRIMARY)
    txt.move_to(rect.get_center())
    return VGroup(rect, txt)


def make_cell_row(
    labels: list,
    color: str = ACCENT_BLUE,
    cell_width: float = 0.8,
    cell_height: float = 0.6,
    buff: float = 0.0,
    font_size: int = LABEL_SIZE,
) -> VGroup:
    """Horizontal row of rounded-rect cells."""
    cells = VGroup(*[
        make_cell(lbl, cell_width, cell_height, color, font_size)
        for lbl in labels
    ])
    cells.arrange(RIGHT, buff=buff)
    return cells


# ── Helper: Code Block ───────────────────────────────────────────────────────
def make_code_block(
    code_str: str,
    font_size: int = CODE_FONT_SIZE,
    language: str = "python",
) -> Code:
    """Styled code block with consistent look."""
    return Code(
        code_string=code_str,
        language=language,
        formatter_style="monokai",
        background="rectangle",
        add_line_numbers=False,
        background_config={
            "stroke_color": ACCENT_BLUE,
            "stroke_width": 1,
        },
        paragraph_config={
            "font_size": font_size,
        },
    )


# ── Helper: Intro / Outro Sequences ─────────────────────────────────────────
def intro_sequence(scene, title: str, subtitle: str = "", duration: float = 3.0):
    """Play standard branded intro. ~3 seconds."""
    card = make_title_card(title, subtitle)
    scene.play(FadeIn(card, shift=UP * 0.3), run_time=0.8)
    scene.wait(duration - 1.6)
    scene.play(FadeOut(card), run_time=0.8)


def make_mcq_card(
    question: str,
    options: list[str],
    correct_idx: int | None = None,
) -> VGroup:
    """Create a multiple-choice question card.

    Args:
        question: The question text.
        options: List of answer option strings (A, B, C, D labels added automatically).
        correct_idx: If provided, highlight this option in green as the correct answer.

    Returns:
        VGroup containing the question and all option rows.
    """
    labels = "ABCDEFGH"

    q_text = Text(question, font_size=BODY_SIZE, color=TEXT_PRIMARY, weight="BOLD")
    q_text.to_edge(UP, buff=1.0)

    # Clamp the option width to the current frame so portrait (9-wide)
    # doesn't overflow. Landscape's default frame_width is ~14.222,
    # giving back the original 10-unit cards. Portrait's is ~9 wide so
    # we cap at ~8 to leave a 0.5-unit margin each side.
    from manim import config as _manim_config

    option_width = min(10.0, _manim_config.frame_width - 1.0)

    option_vgroup = VGroup()
    for i, opt in enumerate(options):
        letter = labels[i] if i < len(labels) else str(i + 1)
        is_correct = correct_idx is not None and i == correct_idx
        text_color = ACCENT_GREEN if is_correct else TEXT_PRIMARY
        border_color = ACCENT_GREEN if is_correct else TEXT_DIM
        weight = "BOLD" if is_correct else "NORMAL"

        opt_rect = RoundedRectangle(
            corner_radius=0.15,
            width=option_width,
            height=0.7,
            fill_color=ACCENT_GREEN if is_correct else BG_COLOR,
            fill_opacity=0.15 if is_correct else 0.0,
            stroke_color=border_color,
            stroke_width=2 if is_correct else 1,
        )
        opt_text = Text(
            f"{letter})  {opt}",
            font_size=LABEL_SIZE,
            color=text_color,
            weight=weight,
        )
        opt_text.move_to(opt_rect.get_center())
        option_vgroup.add(VGroup(opt_rect, opt_text))

    option_vgroup.arrange(DOWN, buff=0.2)
    option_vgroup.next_to(q_text, DOWN, buff=0.6)

    return VGroup(q_text, option_vgroup).move_to(ORIGIN)


def outro_sequence(
    scene,
    text: str = "Octoflash AI",
    tagline: str = "Generated from one prompt.",
    url: str = "Make yours at octoflash.ai",
    duration: float = 3.0,
):
    """End-card outro: brand mark + tagline + call-to-action URL.

    Layout (stacked, centered):
        [ Octoflash AI ]                ← 84pt bold
        Generated from one prompt.      ← 32pt, dimmed
        Make yours at octoflash.ai      ← 28pt, dimmed

    The `text` / `tagline` / `url` parameters keep the function reusable for
    per-project end-cards while defaulting to the standard brand strings.
    """
    brand = Text(text, font_size=84, color=TEXT_PRIMARY, weight="BOLD")
    line = Text(tagline, font_size=32, color=TEXT_PRIMARY).set_opacity(0.85)
    link = Text(url, font_size=28, color=TEXT_PRIMARY).set_opacity(0.65)

    stack = VGroup(brand, line, link).arrange(DOWN, buff=0.32).move_to(ORIGIN)

    scene.play(FadeIn(stack, scale=0.9), run_time=0.8)
    scene.wait(max(0.1, duration - 1.6))
    scene.play(FadeOut(stack), run_time=0.8)
