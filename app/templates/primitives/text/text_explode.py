"""text_explode — characters fly outward from a point."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class TextExplodeConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 80.0
    origin: Literal["center", "top", "bottom"] = "center"
    distance: float = Field(default=4.0, gt=0.0)  # in Manim units
    rotate: bool = True


@register
class TextExplodePrimitive(Primitive):
    PRIMITIVE_ID = "text_explode"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = TextExplodeConfig
    IMPLEMENTED = True

    def build(self, config: TextExplodeConfig, ctx: PrimitiveContext) -> None:
        import numpy as np
        from manim import DOWN, FadeOut, ORIGIN, Text, UP

        text = Text(config.text, color=config.color, font_size=config.size)
        origin_offset = {
            "center": ORIGIN,
            "top": UP * 2.5,
            "bottom": DOWN * 2.5,
        }[config.origin]
        text.move_to(origin_offset)
        ctx.scene.add(text)

        # Random radial offset per character.
        rng = np.random.default_rng(seed=ctx.t.__hash__() if ctx.t else None)
        animations = []
        for char in text:
            angle = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(config.distance * 0.5, config.distance)
            target = np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
            anim = char.animate.shift(target)
            if config.rotate:
                anim = anim.rotate(rng.uniform(-np.pi, np.pi))
            animations.append(anim)

        run_time = float(ctx.duration) if ctx.duration is not None else 1.0
        ctx.scene.play(*animations, run_time=run_time)
        # Fade out so subsequent steps start on a clean canvas.
        ctx.scene.play(FadeOut(text), run_time=0.2)
