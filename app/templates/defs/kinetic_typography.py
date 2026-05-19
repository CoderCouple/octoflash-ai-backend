"""kinetic_typography — words size/position dance per beat."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    NumberParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="kinetic_typography",
    version="1.0.0",
    name="Kinetic Typography",
    category="text_titles",
    glyph="kinetic_typography",
    manic_compatible=False,
    description="Words size/position dance per beat.",
    params=[
        StringParam(name="text", label="Phrase (space-separated words)", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        NumberParam(name="beat_seconds", label="Beat length", default=0.25, min=0.1, max=1.0),
        NumberParam(name="scale_variance", label="Scale variance", default=0.4, min=0.0, max=1.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="kinetic_text",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "beat_seconds": "${params.beat_seconds}",
                "scale_variance": "${params.scale_variance}",
            },
            at=0.0,
            label="dance",
        ),
    ],
    default_duration=4.0,
)
