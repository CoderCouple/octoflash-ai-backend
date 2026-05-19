"""text_split — single line splits into two lines that drift apart."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class TextSplitConfig(BaseModel):
    line_one: str
    line_two: str
    color: str = "#FFFFFF"
    size: float = 80.0
    split_distance: float = Field(default=1.5, gt=0.0)


@register
class TextSplitPrimitive(Primitive):
    PRIMITIVE_ID = "text_split"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = TextSplitConfig
    IMPLEMENTED = True

    def build(self, config: TextSplitConfig, ctx: PrimitiveContext) -> None:
        from manim import DOWN, FadeIn, ORIGIN, Text, UP, rate_functions

        line_one = Text(config.line_one, color=config.color, font_size=config.size)
        line_two = Text(config.line_two, color=config.color, font_size=config.size)
        # Start both lines overlapping at origin.
        line_one.move_to(ORIGIN)
        line_two.move_to(ORIGIN)
        ctx.scene.add(line_one, line_two)

        run_time = float(ctx.duration) if ctx.duration is not None else 1.0
        # Fade in (both at origin look like one line), then split apart.
        ctx.scene.play(FadeIn(line_one), FadeIn(line_two), run_time=run_time * 0.4)
        ctx.scene.play(
            line_one.animate.shift(UP * config.split_distance),
            line_two.animate.shift(DOWN * config.split_distance),
            run_time=run_time * 0.6,
            rate_func=rate_functions.ease_out_cubic,
        )
