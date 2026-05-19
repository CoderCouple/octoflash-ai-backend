"""subtitle_stack — title above, subtitle slides in below."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="subtitle_stack",
    version="1.0.0",
    name="Subtitle Stack",
    category="text_titles",
    glyph="subtitle_stack",
    manic_compatible=False,
    description="Title above, subtitle slides in below.",
    params=[
        StringParam(name="title", label="Title", required=True),
        StringParam(name="subtitle", label="Subtitle", required=True),
        ColorParam(name="title_color", label="Title color", default="#FFFFFF"),
        ColorParam(name="subtitle_color", label="Subtitle color", default="#AAAAAA"),
        ColorParam(name="bg_color", label="Background", default="#000000"),
        DurationParam(name="hold_seconds", label="Hold", default=2.0, min=0.5, max=10.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="text_reveal",
            bind={
                "text": "${params.title}",
                "color": "${params.title_color}",
                "direction": "fade",
                "size": 88.0,
                "y_align": "top",
            },
            at=0.0,
            duration=0.6,
            label="reveal title",
        ),
        StepSpec(
            primitive="text_reveal",
            bind={
                "text": "${params.subtitle}",
                "color": "${params.subtitle_color}",
                "direction": "up",
                "size": 40.0,
                "y_align": "bottom",
            },
            at=0.6,
            duration=0.6,
            label="slide in subtitle",
        ),
        StepSpec(primitive="hold", bind={}, at=1.2, duration="${params.hold_seconds}"),
    ],
    default_duration=3.5,
)
