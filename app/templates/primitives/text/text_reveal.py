"""
text_reveal — fade/slide a single string into the scene.

Used by: title_reveal, big_quote, chapter_card, lower_third, tagline_split.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class TextRevealConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 72.0
    direction: Literal["up", "down", "left", "right", "fade"] = "up"
    font: str | None = None
    x_align: Literal["left", "center", "right"] = "center"
    y_align: Literal["top", "middle", "bottom"] = "middle"
    easing: Literal["linear", "ease_in", "ease_out", "ease_in_out"] = "ease_out"
    delay_per_word: float = Field(default=0.0, ge=0.0)


@register
class TextRevealPrimitive(Primitive):
    PRIMITIVE_ID = "text_reveal"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = TextRevealConfig
    IMPLEMENTED = True

    def build(self, config: TextRevealConfig, ctx: PrimitiveContext) -> None:
        # Lazy Manim import — Cairo/Pango load is heavy; avoid at module-import time.
        from manim import DOWN, FadeIn, LEFT, ORIGIN, RIGHT, UP, Text

        text_kwargs: dict = {"color": config.color, "font_size": config.size}
        if config.font:
            text_kwargs["font"] = config.font
        mobject = Text(config.text, **text_kwargs)

        # Anchor position from y_align.
        if config.y_align == "top":
            mobject.to_edge(UP)
        elif config.y_align == "bottom":
            mobject.to_edge(DOWN)
        else:
            mobject.move_to(ORIGIN)

        # Optional shift for non-fade directions (start off-screen-ish, slide in).
        offset = {
            "up": DOWN * 1.0,
            "down": UP * 1.0,
            "left": RIGHT * 1.0,
            "right": LEFT * 1.0,
            "fade": ORIGIN * 0,
        }[config.direction]
        if config.direction != "fade":
            mobject.shift(offset)

        run_time = float(ctx.duration) if ctx.duration is not None else 1.0
        if config.direction == "fade":
            ctx.scene.play(FadeIn(mobject), run_time=run_time)
        else:
            # Slide back to the anchor position + write.
            ctx.scene.play(
                FadeIn(mobject, shift=-offset),
                run_time=run_time,
            )
        # Leave the mobject on the scene so subsequent steps (hold, etc.) see it.
