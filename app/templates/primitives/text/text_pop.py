"""text_pop — punch-in scale with optional micro-shake. Manic-friendly."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class TextPopConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 96.0
    scale_from: float = Field(default=0.6, gt=0.0)
    shake_intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    x_align: str = "center"
    y_align: str = "middle"


@register
class TextPopPrimitive(Primitive):
    PRIMITIVE_ID = "text_pop"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = TextPopConfig
    IMPLEMENTED = True

    def build(self, config: TextPopConfig, ctx: PrimitiveContext) -> None:
        import numpy as np
        from manim import ORIGIN, Text, rate_functions

        text = Text(config.text, color=config.color, font_size=config.size)
        text.move_to(ORIGIN)
        # Start small so the play() animates it growing into final size.
        text.scale(config.scale_from)
        ctx.scene.add(text)

        # Punch in.
        ctx.scene.play(
            text.animate.scale(1.0 / config.scale_from),
            run_time=float(ctx.duration) if ctx.duration is not None else 0.4,
            rate_func=rate_functions.ease_out_back,
        )

        # Optional micro-shake: small jittered displacements after the pop.
        if config.shake_intensity > 0:
            shake_amount = 0.05 * config.shake_intensity
            for _ in range(4):
                offset = np.array([
                    np.random.uniform(-shake_amount, shake_amount),
                    np.random.uniform(-shake_amount, shake_amount),
                    0.0,
                ])
                ctx.scene.play(text.animate.shift(offset), run_time=0.04)
                ctx.scene.play(text.animate.shift(-offset), run_time=0.04)
