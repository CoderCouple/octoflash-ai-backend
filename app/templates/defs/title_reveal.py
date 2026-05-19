"""
title_reveal — single line fades up + holds.

Reference template definition. The pattern for all 127 templates:
declare params, declare steps that compose primitives, declare style modifiers.
"""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    StepSpec,
    StringParam,
    StyleModifier,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="title_reveal",
    version="1.0.0",
    name="Title Reveal",
    category="text_titles",
    glyph="title_reveal",
    manic_compatible=True,
    description="Single line fades up + holds.",
    params=[
        StringParam(name="title", label="Title", required=True),
        StringParam(name="subtitle", label="Subtitle", default=""),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#000000"),
        DurationParam(
            name="hold_seconds", label="Hold duration", default=2.0, min=0.5, max=10.0
        ),
    ],
    steps=[
        StepSpec(
            primitive="text_reveal",
            bind={
                "text": "${params.title}",
                "color": "${params.color}",
                "direction": "up",
                "size": 96.0,
            },
            at=0.0,
            duration=1.0,
            label="reveal title",
        ),
        StepSpec(
            primitive="hold",
            bind={},
            at=1.0,
            duration="${params.hold_seconds}",
            label="dwell on title",
        ),
    ],
    style_modifiers={
        "manic": StyleModifier(
            duration_scale=0.6,
            add_shake=True,
            caption_size_scale=1.4,
            cut_style="hard",
        ),
    },
    default_duration=3.5,
)
