"""tagline_split — title splits into two lines that drift apart."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    NumberParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="tagline_split",
    version="1.0.0",
    name="Tagline Split",
    category="text_titles",
    glyph="tagline_split",
    manic_compatible=False,
    description="Title splits into two lines that drift apart.",
    params=[
        StringParam(name="line_one", label="Line 1", required=True),
        StringParam(name="line_two", label="Line 2", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        NumberParam(name="split_distance", label="Split distance", default=1.5, min=0.5, max=4.0),
        DurationParam(name="hold_seconds", label="Hold", default=2.0, min=0.5, max=8.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="text_split",
            bind={
                "line_one": "${params.line_one}",
                "line_two": "${params.line_two}",
                "color": "${params.color}",
                "split_distance": "${params.split_distance}",
            },
            at=0.0,
            duration=0.9,
            label="split apart",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=3.5,
)
