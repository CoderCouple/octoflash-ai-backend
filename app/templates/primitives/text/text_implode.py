"""text_implode — characters fly inward to assemble a word."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class TextImplodeConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 80.0
    from_distance: float = Field(default=5.0, gt=0.0)
    rotate: bool = True


@register
class TextImplodePrimitive(Primitive):
    PRIMITIVE_ID = "text_implode"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = TextImplodeConfig
    IMPLEMENTED = True

    def build(self, config: TextImplodeConfig, ctx: PrimitiveContext) -> None:
        import numpy as np
        from manim import Text

        text = Text(config.text, color=config.color, font_size=config.size)
        # Capture final positions (where each char will end up).
        final_positions = [char.get_center().copy() for char in text]

        # Scatter each char to a random initial position; optionally rotate.
        rng = np.random.default_rng()
        for char in text:
            angle = rng.uniform(0, 2 * np.pi)
            r = rng.uniform(config.from_distance * 0.5, config.from_distance)
            char.shift(np.array([r * np.cos(angle), r * np.sin(angle), 0.0]))
            if config.rotate:
                char.rotate(rng.uniform(-np.pi, np.pi))
        ctx.scene.add(text)

        # Animate each char back to its final (assembled) position.
        animations = []
        for char, target in zip(text, final_positions):
            anim = char.animate.move_to(target)
            if config.rotate:
                anim = anim.set_angle(0)
            animations.append(anim)

        run_time = float(ctx.duration) if ctx.duration is not None else 1.0
        ctx.scene.play(*animations, run_time=run_time)
