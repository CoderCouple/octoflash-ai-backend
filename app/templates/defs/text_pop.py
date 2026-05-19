"""text_pop — punch-in scale + micro-shake, holds. Manic-friendly."""

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
    id="text_pop",
    version="1.0.0",
    name="Text Pop",
    category="text_titles",
    glyph="text_pop",
    manic_compatible=True,
    description="Punch in, micro-shake, hold.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#000000"),
        NumberParam(name="shake", label="Shake intensity", default=0.4, min=0.0, max=1.0),
        DurationParam(name="hold_seconds", label="Hold", default=1.8, min=0.5, max=8.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="text_pop",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "shake_intensity": "${params.shake}",
            },
            at=0.0,
            duration=0.5,
            label="punch in",
        ),
        StepSpec(primitive="hold", bind={}, at=0.5, duration="${params.hold_seconds}"),
    ],
    style_modifiers={
        "manic": StyleModifier(duration_scale=0.55, add_shake=True, cut_style="hard"),
    },
    default_duration=2.5,
)
