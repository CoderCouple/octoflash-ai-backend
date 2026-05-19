"""text_explode — characters fly out from a point."""

from app.templates.schema import (
    BoolParam,
    ColorParam,
    DurationParam,
    EnumParam,
    NumberParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="text_explode",
    version="1.0.0",
    name="Text Explode",
    category="text_titles",
    glyph="text_explode",
    manic_compatible=False,
    description="Characters fly out from a point.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#000000"),
        EnumParam(name="origin", label="Explosion origin",
                  choices=["center", "top", "bottom"], default="center"),
        NumberParam(name="distance", label="Travel distance", default=4.0, min=1.0, max=10.0),
        BoolParam(name="rotate", label="Rotate while flying", default=True),
        DurationParam(name="explode_seconds", label="Explosion length", default=1.0, min=0.3, max=4.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="text_explode",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "origin": "${params.origin}",
                "distance": "${params.distance}",
                "rotate": "${params.rotate}",
            },
            at=0.0,
            duration="${params.explode_seconds}",
            label="explode",
        ),
    ],
    default_duration=1.5,
)
