"""typewriter — types text one character at a time."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class TypewriterConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 56.0
    chars_per_second: float = Field(default=20.0, gt=0.0)
    cursor: bool = True
    cursor_color: str = "#FFFFFF"


@register
class TypewriterPrimitive(Primitive):
    PRIMITIVE_ID = "typewriter"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = TypewriterConfig
    IMPLEMENTED = True

    def build(self, config: TypewriterConfig, ctx: PrimitiveContext) -> None:
        from manim import AddTextLetterByLetter, RIGHT, Text

        text = Text(config.text, color=config.color, font_size=config.size)
        ctx.scene.add(text)

        type_seconds = max(len(config.text) / config.chars_per_second, 0.01)
        run_time = float(ctx.duration) if ctx.duration is not None else type_seconds
        run_time = max(run_time, type_seconds)
        ctx.scene.play(AddTextLetterByLetter(text, run_time=run_time))

        # Static cursor at the end — blinking via updater is fragile across
        # Manim versions; ship the simpler variant.
        if config.cursor:
            cursor = Text("|", color=config.cursor_color, font_size=config.size)
            cursor.next_to(text, RIGHT, buff=0.05)
            ctx.scene.add(cursor)
