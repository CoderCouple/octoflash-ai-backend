"""typewriter — types one character at a time."""

from app.templates.schema import (
    BoolParam,
    ColorParam,
    DurationParam,
    NumberParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="typewriter",
    version="1.0.0",
    name="Typewriter",
    category="text_titles",
    glyph="typewriter",
    manic_compatible=False,
    description="Types one character at a time.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        NumberParam(name="chars_per_second", label="Typing speed", default=24.0, min=4.0, max=120.0),
        BoolParam(name="cursor", label="Show cursor", default=True),
        DurationParam(name="hold_seconds", label="Hold after", default=1.5, min=0.0, max=10.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="typewriter",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "chars_per_second": "${params.chars_per_second}",
                "cursor": "${params.cursor}",
            },
            at=0.0,
            label="type out",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=4.0,
)
