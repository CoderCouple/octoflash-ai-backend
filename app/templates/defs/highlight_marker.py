"""highlight_marker — yellow marker swipes over a key phrase."""

from app.templates.schema import (
    ColorParam,
    DurationParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="highlight_marker",
    version="1.0.0",
    name="Highlight Marker",
    category="text_titles",
    glyph="highlight_marker",
    manic_compatible=False,
    description="Yellow marker swipes over a key phrase.",
    params=[
        StringParam(name="text", label="Full text", required=True),
        StringParam(
            name="highlight_substring",
            label="Substring to highlight (must appear in text)",
            required=True,
        ),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="highlight_color", label="Marker color", default="#FFD400"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        DurationParam(name="swipe_seconds", label="Marker swipe time", default=0.4, min=0.1, max=2.0),
        DurationParam(name="hold_seconds", label="Hold after", default=2.0, min=0.5, max=8.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="text_reveal",
            bind={"text": "${params.text}", "color": "${params.color}", "direction": "fade"},
            at=0.0,
            duration=0.5,
            label="reveal text",
        ),
        StepSpec(
            primitive="highlight_swipe",
            bind={
                "text": "${params.text}",
                "highlight_substring": "${params.highlight_substring}",
                "color": "${params.color}",
                "highlight_color": "${params.highlight_color}",
                "swipe_seconds": "${params.swipe_seconds}",
            },
            at=0.5,
            duration="${params.swipe_seconds}",
            label="marker swipe",
        ),
        StepSpec(primitive="hold", bind={}, duration="${params.hold_seconds}"),
    ],
    default_duration=3.2,
)
