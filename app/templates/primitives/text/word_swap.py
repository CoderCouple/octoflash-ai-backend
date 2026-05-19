"""word_swap — one word in a sentence cycles through alternatives."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class WordSwapConfig(BaseModel):
    sentence_before: str = ""
    words: list[str]  # cycles through these in order
    sentence_after: str = ""
    color: str = "#FFFFFF"
    swap_color: str = "#00FFAA"  # color applied to the swapping word
    size: float = 64.0
    seconds_per_word: float = Field(default=0.6, gt=0.0)


@register
class WordSwapPrimitive(Primitive):
    PRIMITIVE_ID = "word_swap"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = WordSwapConfig
    IMPLEMENTED = True

    def build(self, config: WordSwapConfig, ctx: PrimitiveContext) -> None:
        from manim import ORIGIN, ReplacementTransform, RIGHT, Text, VGroup

        def _make_group(word: str) -> VGroup:
            parts = []
            if config.sentence_before:
                parts.append(
                    Text(config.sentence_before, color=config.color, font_size=config.size)
                )
            parts.append(Text(word, color=config.swap_color, font_size=config.size))
            if config.sentence_after:
                parts.append(
                    Text(config.sentence_after, color=config.color, font_size=config.size)
                )
            return VGroup(*parts).arrange(RIGHT, buff=0.18).move_to(ORIGIN)

        if not config.words:
            return  # nothing to swap

        group = _make_group(config.words[0])
        ctx.scene.add(group)

        # Hold the first word briefly before swapping.
        ctx.scene.wait(config.seconds_per_word * 0.5)

        for next_word in config.words[1:]:
            new_group = _make_group(next_word)
            ctx.scene.play(
                ReplacementTransform(group, new_group),
                run_time=config.seconds_per_word,
            )
            group = new_group
            ctx.scene.wait(config.seconds_per_word * 0.3)
