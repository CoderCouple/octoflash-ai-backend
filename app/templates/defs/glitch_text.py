"""glitch_text — RGB-split + datamosh reveal. Manic-friendly."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    NumberParam,
    StepSpec,
    StringParam,
    StyleModifier,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="glitch_text",
    version="1.0.0",
    name="Glitch Text",
    category="text_titles",
    glyph="glitch_text",
    manic_compatible=True,
    description="RGB-split + datamosh reveal.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Base color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#000000"),
        NumberParam(name="intensity", label="Glitch intensity", default=0.6, min=0.0, max=1.0),
        DurationParam(name="hold_seconds", label="Hold", default=1.5, min=0.5, max=6.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="glitch_text",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "glitch_intensity": "${params.intensity}",
            },
            at=0.0,
            duration=0.8,
            label="glitch in",
        ),
        StepSpec(primitive="hold", bind={}, at=0.8, duration="${params.hold_seconds}"),
    ],
    style_modifiers={
        "manic": StyleModifier(duration_scale=0.5, add_shake=True, cut_style="hard"),
    },
    default_duration=2.5,
)
