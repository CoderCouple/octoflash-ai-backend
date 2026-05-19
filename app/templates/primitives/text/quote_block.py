"""quote_block — large quote text + attribution bar below."""

from __future__ import annotations

from pydantic import BaseModel

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class QuoteBlockConfig(BaseModel):
    quote: str
    attribution: str = ""
    color: str = "#FFFFFF"
    quote_size: float = 64.0
    attribution_size: float = 28.0
    attribution_color: str = "#AAAAAA"


@register
class QuoteBlockPrimitive(Primitive):
    PRIMITIVE_ID = "quote_block"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = QuoteBlockConfig
    IMPLEMENTED = True

    def build(self, config: QuoteBlockConfig, ctx: PrimitiveContext) -> None:
        from manim import DOWN, FadeIn, GrowFromCenter, Line, Text, VGroup

        quote_text = Text(
            f"“{config.quote}”",
            color=config.color,
            font_size=config.quote_size,
        )
        divider = Line(
            start=[-2, 0, 0], end=[2, 0, 0],
            color=config.attribution_color,
            stroke_width=2,
        )
        attribution = Text(
            f"— {config.attribution}" if config.attribution else "",
            color=config.attribution_color,
            font_size=config.attribution_size,
        )

        group = VGroup(quote_text, divider, attribution)
        group.arrange(DOWN, buff=0.4)
        ctx.scene.add(group)

        run_time = float(ctx.duration) if ctx.duration is not None else 1.0
        ctx.scene.play(FadeIn(quote_text, shift=DOWN * 0.3), run_time=run_time * 0.45)
        ctx.scene.play(GrowFromCenter(divider), run_time=run_time * 0.2)
        if config.attribution:
            ctx.scene.play(FadeIn(attribution), run_time=run_time * 0.35)
