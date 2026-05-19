"""acronym_expand — letters become full words (A.P.I. → Application Programming Interface)."""

from app.templates.schema import (
    ColorParam,
    ListParam,
    StepSpec,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="acronym_expand",
    version="1.0.0",
    name="Acronym Expand",
    category="text_titles",
    glyph="acronym_expand",
    manic_compatible=False,
    description="Letters become full words (A.P.I. → Application Programming Interface).",
    params=[
        ListParam(
            name="letters",
            label="Letters",
            required=True,
            min_items=2,
            max_items=8,
            default=["A", "P", "I"],
        ),
        ListParam(
            name="expansions",
            label="Expansions (same length as letters)",
            required=True,
            min_items=2,
            max_items=8,
            default=["Application", "Programming", "Interface"],
        ),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="accent_color", label="Leading-letter accent", default="#FF6B35"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="acronym_expand",
            bind={
                "letters": "${params.letters}",
                "expansions": "${params.expansions}",
                "color": "${params.color}",
                "accent_color": "${params.accent_color}",
            },
            at=0.0,
            label="expand letters",
        ),
    ],
    default_duration=4.5,
)
