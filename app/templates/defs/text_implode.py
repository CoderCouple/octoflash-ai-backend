"""text_implode — characters fly inward to form the word."""

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
    id="text_implode",
    version="1.0.0",
    name="Text Implode",
    category="text_titles",
    glyph="text_implode",
    manic_compatible=False,
    description="Characters fly in to form the word.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#000000"),
        NumberParam(name="from_distance", label="Starting distance", default=5.0, min=1.0, max=12.0),
        BoolParam(name="rotate", label="Rotate while flying", default=True),
        DurationParam(name="implode_seconds", label="Implosion length", default=1.0, min=0.3, max=4.0),
        DurationParam(name="hold_seconds", label="Hold after", default=1.5, min=0.0, max=8.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="text_implode",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "from_distance": "${params.from_distance}",
                "rotate": "${params.rotate}",
            },
            at=0.0,
            duration="${params.implode_seconds}",
            label="implode",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=2.5,
)
