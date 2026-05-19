"""handwritten_text — strokes on like a signature."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class HandwrittenTextConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 84.0
    font: str = "Caveat"  # any handwritten-style system font
    stroke_seconds: float = Field(default=1.5, gt=0.0)


@register
class HandwrittenTextPrimitive(Primitive):
    PRIMITIVE_ID = "handwritten_text"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = HandwrittenTextConfig
    IMPLEMENTED = True

    def build(self, config: HandwrittenTextConfig, ctx: PrimitiveContext) -> None:
        import logging

        from manim import Text, Write

        logger = logging.getLogger(__name__)

        # Try declared font; on any failure (font missing, Pango error, etc.),
        # fall back to Manim default and log a warning that the substitution
        # happened. Audit-visible via the worker log.
        try:
            text = Text(
                config.text,
                font=config.font,
                color=config.color,
                font_size=config.size,
            )
        except Exception as e:
            logger.warning(
                "handwritten_text: font %r unavailable (%s); falling back to default",
                config.font, type(e).__name__,
            )
            text = Text(config.text, color=config.color, font_size=config.size)

        run_time = float(ctx.duration) if ctx.duration is not None else config.stroke_seconds
        ctx.scene.play(Write(text), run_time=run_time)
