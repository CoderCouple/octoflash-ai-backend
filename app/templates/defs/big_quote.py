"""big_quote — pull-quote with attribution bar."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="big_quote",
    version="1.0.0",
    name="Big Quote",
    category="text_titles",
    glyph="big_quote",
    manic_compatible=False,
    description="Pull-quote with attribution bar.",
    params=[
        StringParam(name="quote", label="Quote", required=True),
        StringParam(name="attribution", label="Attribution", default=""),
        ColorParam(name="quote_color", label="Quote color", default="#FFFFFF"),
        ColorParam(name="attribution_color", label="Attribution color", default="#888888"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        DurationParam(name="hold_seconds", label="Hold", default=3.0, min=1.0, max=12.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="quote_block",
            bind={
                "quote": "${params.quote}",
                "attribution": "${params.attribution}",
                "color": "${params.quote_color}",
                "attribution_color": "${params.attribution_color}",
            },
            at=0.0,
            duration=1.0,
            label="reveal quote",
        ),
        StepSpec(primitive="hold", bind={}, at=1.0, duration="${params.hold_seconds}"),
    ],
    default_duration=4.5,
)
