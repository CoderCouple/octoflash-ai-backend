"""text_reveal_mask — text masked behind a sweeping bar."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    EnumParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="text_reveal_mask",
    version="1.0.0",
    name="Text Reveal Mask",
    category="text_titles",
    glyph="text_reveal_mask",
    manic_compatible=False,
    description="Text masked behind a sweeping bar.",
    params=[
        StringParam(name="text", label="Text", required=True),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        ColorParam(name="mask_color", label="Mask color", default="#FF6B35"),
        EnumParam(
            name="sweep",
            label="Sweep direction",
            choices=["left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"],
            default="left_to_right",
        ),
        DurationParam(name="hold_seconds", label="Hold", default=1.8, min=0.5, max=8.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="text_mask_wipe",
            bind={
                "text": "${params.text}",
                "color": "${params.color}",
                "mask_color": "${params.mask_color}",
                "sweep": "${params.sweep}",
            },
            at=0.0,
            duration=0.7,
            label="wipe reveal",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=2.8,
)
