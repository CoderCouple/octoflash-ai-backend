"""
Pydantic schema for declarative template definitions.

A TemplateDefinition is the entire spec for one of Octoflash's templates,
expressed as data:
  - what params it accepts (typed, discriminated union)
  - what reusable primitives it composes (steps)
  - how each style preset modifies the base render (style_modifiers)

Template defs live at app/templates/defs/<id>.py, each exporting:
    TEMPLATE: TemplateDefinition = TemplateDefinition(...)

The loader (app/templates/loader.py) imports and validates them.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

# ─── Parameter specs (discriminated union) ─────────────────────────────────────


class _ParamBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    required: bool = False
    description: str | None = None


class StringParam(_ParamBase):
    type: Literal["string"] = "string"
    default: str | None = None
    min_length: int | None = None
    max_length: int | None = None


class NumberParam(_ParamBase):
    type: Literal["number"] = "number"
    default: float | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None


class ColorParam(_ParamBase):
    type: Literal["color"] = "color"
    default: str | None = None  # hex string like "#FFFFFF"


class EnumParam(_ParamBase):
    type: Literal["enum"] = "enum"
    choices: list[str]
    default: str | None = None


class ImageParam(_ParamBase):
    type: Literal["image"] = "image"
    default: str | None = None  # URL or asset id


class BoolParam(_ParamBase):
    type: Literal["bool"] = "bool"
    default: bool | None = None


class DurationParam(_ParamBase):
    type: Literal["duration"] = "duration"
    default: float | None = None  # seconds
    min: float | None = None
    max: float | None = None


class ListParam(_ParamBase):
    """Ordered list of strings — e.g. swap-word options, acronym expansions."""

    type: Literal["list"] = "list"
    default: list[str] | None = None
    min_items: int | None = None
    max_items: int | None = None


ParamSpec = Annotated[
    Union[
        StringParam,
        NumberParam,
        ColorParam,
        EnumParam,
        ImageParam,
        BoolParam,
        DurationParam,
        ListParam,
    ],
    Field(discriminator="type"),
]


# ─── Step (one primitive invocation) ───────────────────────────────────────────


class StepSpec(BaseModel):
    """One step in the render — invoke a primitive with bound config."""

    model_config = ConfigDict(extra="forbid")

    primitive: str
    """Primitive id, e.g. "text_reveal". Must exist in PRIMITIVES registry."""

    bind: dict[str, Any] = Field(default_factory=dict)
    """Config passed to the primitive. Values may use "${params.foo}" to
    interpolate template params at render time."""

    at: float = 0.0
    """Start time within the scene, in seconds (post style-modifier scaling)."""

    duration: float | str | None = None
    """How long this step animates. None = primitive's natural duration.
    May also be a "${params.foo}" interpolation string."""

    label: str | None = None
    """Optional human label for the step — used in render logs / debug UI."""


# ─── Style modifiers (per-preset overrides on top of base steps) ───────────────


class StyleModifier(BaseModel):
    """How a StylePreset (manic / classic_3b1b / kurzgesagt / …) transforms a render."""

    model_config = ConfigDict(extra="forbid")

    duration_scale: float | None = None
    """Multiply every step's duration (and `at`) by this. <1 = faster."""

    add_shake: bool = False
    """Apply micro-shake to all elements (Manic preset hallmark)."""

    caption_size_scale: float | None = None
    """Multiply text/caption sizes (e.g. 1.4 for oversized Manic captions)."""

    cut_style: Literal["soft", "hard"] | None = None
    """soft = crossfade between steps; hard = instant cut (Manic)."""

    extra_steps: list[StepSpec] = Field(default_factory=list)
    """Additional steps appended after the base steps (e.g. callout flashes)."""

    palette_override: dict[str, str] | None = None
    """Override colors by semantic name, e.g. {"bg": "#0A0A0A", "fg": "#00FFAA"}."""


# ─── Top-level template definition ─────────────────────────────────────────────


class TemplateDefinition(BaseModel):
    """The full spec for one template. One per file under app/templates/defs/."""

    model_config = ConfigDict(extra="forbid")

    id: str
    """Stable id like "title_reveal" — used as the key everywhere (scene.template, URLs, file name)."""

    version: str
    """Manual semver, e.g. "1.2.0". Bump on intentional behavior changes —
    used alongside the auto-content-hash to record what was actually rendered."""

    name: str
    """Human label shown in the template library UI."""

    category: str
    """One of TemplateCategory values."""

    glyph: str
    """Icon id for the frontend's template library — usually same as `id`."""

    manic_compatible: bool = False
    """True if pairing with the `manic` StylePreset produces a sensible render."""

    description: str | None = None

    params: list[ParamSpec] = Field(default_factory=list)
    """Tunable inputs the user can set per scene."""

    steps: list[StepSpec] = Field(default_factory=list)
    """Ordered render program — primitives + bindings."""

    style_modifiers: dict[str, StyleModifier] = Field(default_factory=dict)
    """Keyed by StylePreset string (editorial / manic / …)."""

    default_duration: float = 5.0
    """Suggested scene duration in seconds if the user doesn't override."""

    default_size: tuple[int, int] = (1920, 1080)
    """Render resolution (w, h). Most templates inherit project-wide setting."""
