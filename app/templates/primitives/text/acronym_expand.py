"""acronym_expand — letters become full words (A.P.I. → Application Programming Interface)."""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class AcronymExpandConfig(BaseModel):
    letters: list[str]      # ["A", "P", "I"]
    expansions: list[str]   # ["Application", "Programming", "Interface"]
    color: str = "#FFFFFF"
    accent_color: str = "#FF6B35"  # applied to leading letter of each expansion
    letter_size: float = 144.0
    expansion_size: float = 48.0

    @model_validator(mode="after")
    def _same_length(self) -> "AcronymExpandConfig":
        if len(self.letters) != len(self.expansions):
            raise ValueError("`letters` and `expansions` must have the same length")
        return self


@register
class AcronymExpandPrimitive(Primitive):
    PRIMITIVE_ID = "acronym_expand"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = AcronymExpandConfig
    IMPLEMENTED = True

    def build(self, config: AcronymExpandConfig, ctx: PrimitiveContext) -> None:
        from manim import (
            DOWN, FadeIn, LEFT, ORIGIN, ReplacementTransform, RIGHT, Text, VGroup,
        )

        # Phase 1: horizontal row of large letters, centered.
        row = VGroup(*[
            Text(letter, color=config.color, font_size=config.letter_size)
            for letter in config.letters
        ])
        row.arrange(RIGHT, buff=0.4).move_to(ORIGIN)

        # Phase 2: vertical list — one row per (letter, expansion) pair.
        # Color the leading character of each expansion with `accent_color`
        # via Text's t2c (text-to-color) slice map.
        end_group = VGroup()
        for letter, expansion in zip(config.letters, config.expansions):
            letter_mob = Text(letter, color=config.accent_color, font_size=config.letter_size)
            if expansion:
                exp_mob = Text(
                    expansion,
                    color=config.color,
                    font_size=config.expansion_size,
                    t2c={"[0:1]": config.accent_color},
                )
            else:
                exp_mob = Text("", color=config.color, font_size=config.expansion_size)
            pair = VGroup(letter_mob, exp_mob).arrange(RIGHT, buff=0.3)
            end_group.add(pair)
        end_group.arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to(ORIGIN)

        total = float(ctx.duration) if ctx.duration is not None else 4.0
        ctx.scene.play(FadeIn(row), run_time=total * 0.25)
        ctx.scene.wait(total * 0.15)
        ctx.scene.play(ReplacementTransform(row, end_group), run_time=total * 0.45)
        ctx.scene.wait(total * 0.15)
