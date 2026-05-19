"""chapter_card — full-screen chapter number + title."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="chapter_card",
    version="1.0.0",
    name="Chapter Card",
    category="text_titles",
    glyph="chapter_card",
    manic_compatible=False,
    description="Full-screen chapter number + title.",
    params=[
        StringParam(name="chapter_number", label="Chapter number", default="01"),
        StringParam(name="chapter_title", label="Chapter title", required=True),
        ColorParam(name="number_color", label="Number color", default="#FF6B35"),
        ColorParam(name="title_color", label="Title color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        DurationParam(name="hold_seconds", label="Hold", default=2.5, min=1.0, max=10.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="chapter_card",
            bind={
                "chapter_number": "${params.chapter_number}",
                "chapter_title": "${params.chapter_title}",
                "number_color": "${params.number_color}",
                "title_color": "${params.title_color}",
            },
            at=0.0,
            duration=1.0,
            label="card in",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=4.0,
)
