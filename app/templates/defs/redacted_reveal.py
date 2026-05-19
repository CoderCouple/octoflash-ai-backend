"""redacted_reveal — black bar wipes off to reveal text."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    EnumParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="redacted_reveal",
    version="1.0.0",
    name="Redacted Reveal",
    category="text_titles",
    glyph="redacted_reveal",
    manic_compatible=False,
    description="Black bar wipes off to reveal text.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#FFFFFF"),
        ColorParam(name="redaction_color", label="Redaction bar color", default="#000000"),
        EnumParam(
            name="wipe_direction",
            label="Wipe direction",
            choices=["left_to_right", "right_to_left"],
            default="left_to_right",
        ),
        DurationParam(name="hold_seconds", label="Hold", default=2.0, min=0.5, max=8.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="redacted_text",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "redaction_color": "${params.redaction_color}",
                "wipe_direction": "${params.wipe_direction}",
            },
            at=0.0,
            duration=0.8,
            label="wipe off redaction",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=2.8,
)
