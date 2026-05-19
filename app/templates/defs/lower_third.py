"""lower_third — name/title strip animates in from the corner."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    EnumParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="lower_third",
    version="1.0.0",
    name="Lower Third",
    category="text_titles",
    glyph="lower_third",
    manic_compatible=False,
    description="Name/title strip animates in from the corner.",
    params=[
        StringParam(name="name", label="Name", required=True),
        StringParam(name="title", label="Title / role", default=""),
        ColorParam(name="accent_color", label="Accent color", default="#FF6B35"),
        ColorParam(name="text_color", label="Text color", default="#FFFFFF"),
        ColorParam(name="bar_color", label="Bar color", default="#0A0A0A"),
        EnumParam(
            name="corner",
            label="Corner",
            choices=["bottom_left", "bottom_right"],
            default="bottom_left",
        ),
        DurationParam(name="hold_seconds", label="Hold on screen", default=3.0, min=1.0, max=15.0),
    ],
    steps=[
        StepSpec(
            primitive="lower_third_strip",
            bind={
                "name": "${params.name}",
                "title": "${params.title}",
                "accent_color": "${params.accent_color}",
                "text_color": "${params.text_color}",
                "bar_color": "${params.bar_color}",
                "corner": "${params.corner}",
            },
            at=0.0,
            duration="${params.hold_seconds}",
            label="strip in/hold/out",
        ),
    ],
    default_duration=4.0,
)
