"""word_swap — one word in a sentence cycles through synonyms."""

from app.templates.schema import (
    ColorParam,
    ListParam,
    NumberParam,
    StepSpec,
    StringParam,
    TemplateDefinition,
)

TEMPLATE = TemplateDefinition(
    id="word_swap",
    version="1.0.0",
    name="Word Swap",
    category="text_titles",
    glyph="word_swap",
    manic_compatible=False,
    description="One word in a sentence cycles through synonyms.",
    params=[
        StringParam(name="sentence_before", label="Sentence (before swap word)", default=""),
        ListParam(name="words", label="Swap words", required=True, min_items=2),
        StringParam(name="sentence_after", label="Sentence (after swap word)", default=""),
        ColorParam(name="color", label="Text color", default="#FFFFFF"),
        ColorParam(name="swap_color", label="Swap-word color", default="#00FFAA"),
        ColorParam(name="bg_color", label="Background", default="#0A0A0A"),
        NumberParam(name="seconds_per_word", label="Seconds per swap", default=0.6, min=0.2, max=3.0),
    ],
    steps=[
        StepSpec(primitive="background", bind={"color": "${params.bg_color}"}, at=0.0),
        StepSpec(
            primitive="word_swap",
            bind={
                "sentence_before": "${params.sentence_before}",
                "words": "${params.words}",
                "sentence_after": "${params.sentence_after}",
                "color": "${params.color}",
                "swap_color": "${params.swap_color}",
                "seconds_per_word": "${params.seconds_per_word}",
            },
            at=0.0,
            label="cycle words",
        ),
    ],
    default_duration=4.0,
)
