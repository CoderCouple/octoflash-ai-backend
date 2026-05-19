"""chapter_card — full-screen chapter number + title."""

from __future__ import annotations

from pydantic import BaseModel

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class ChapterCardConfig(BaseModel):
    chapter_number: str  # "01", "II", "Chapter 3" — caller picks the format
    chapter_title: str
    number_color: str = "#FF6B35"
    title_color: str = "#FFFFFF"
    number_size: float = 240.0
    title_size: float = 72.0


@register
class ChapterCardPrimitive(Primitive):
    PRIMITIVE_ID = "chapter_card"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = ChapterCardConfig
    IMPLEMENTED = True

    def build(self, config: ChapterCardConfig, ctx: PrimitiveContext) -> None:
        from manim import DOWN, FadeIn, GrowFromCenter, Line, Text, UP, VGroup

        number = Text(
            config.chapter_number,
            color=config.number_color,
            font_size=config.number_size,
        )
        divider = Line(start=[-2, 0, 0], end=[2, 0, 0], color=config.title_color, stroke_width=2)
        title = Text(
            config.chapter_title,
            color=config.title_color,
            font_size=config.title_size,
        )

        group = VGroup(number, divider, title).arrange(DOWN, buff=0.5)
        ctx.scene.add(group)

        run_time = float(ctx.duration) if ctx.duration is not None else 1.0
        ctx.scene.play(FadeIn(number, shift=UP * 0.5), run_time=run_time * 0.45)
        ctx.scene.play(GrowFromCenter(divider), run_time=run_time * 0.2)
        ctx.scene.play(FadeIn(title), run_time=run_time * 0.35)
