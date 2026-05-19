"""handwritten_signature — text strokes on like a signature."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="handwritten_signature",
    version="1.0.0",
    name="Handwritten Signature",
    category="text_titles",
    glyph="handwritten_signature",
    manic_compatible=False,
    description="Text strokes on like a signature.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Ink color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        StringParam(name="font", label="Font (handwritten-style)", default="Caveat"),
        DurationParam(name="stroke_seconds", label="Stroke time", default=1.6, min=0.5, max=6.0),
        DurationParam(name="hold_seconds", label="Hold after", default=1.5, min=0.0, max=8.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="handwritten_text",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "font": "${params.font}",
                "stroke_seconds": "${params.stroke_seconds}",
            },
            at=0.0,
            duration="${params.stroke_seconds}",
            label="sign",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=3.5,
)
