"""glitch_text — RGB-split reveal with jitter.

Scope cut from the original "RGB-split + datamosh" spec: v1 ships only the
chromatic-aberration + jitter effect (no datamosh). The visual is three
text layers in cyan/magenta/white at slight x-offsets, with brief x-axis
jitter scaled by `glitch_intensity`. Reads as "glitchy reveal" without
needing pixel-level shader work.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class GlitchTextConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 88.0
    glitch_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    rgb_split_pixels: int = Field(default=8, ge=0)


@register
class GlitchTextPrimitive(Primitive):
    PRIMITIVE_ID = "glitch_text"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = GlitchTextConfig
    IMPLEMENTED = True

    def build(self, config: GlitchTextConfig, ctx: PrimitiveContext) -> None:
        import numpy as np
        from manim import FadeIn, FadeOut, LEFT, RIGHT, Text

        # Convert rgb_split_pixels (frontend's mental model) to Manim units.
        # Default frame is 14 units wide ≈ 1920px → 0.0073 unit/px. Use a
        # forgiving conversion since we only need a visible offset.
        split = config.rgb_split_pixels * 0.015

        common = dict(font_size=config.size)
        layer_cyan = Text(config.text, color="#00FFFF", **common)
        layer_magenta = Text(config.text, color="#FF00FF", **common)
        main = Text(config.text, color=config.color, **common)

        # Stack: aberration layers offset on x-axis, main centered.
        layer_cyan.shift(LEFT * split)
        layer_magenta.shift(RIGHT * split)

        # Initial fade-in of the chromatic layers.
        for layer in (layer_cyan, layer_magenta):
            layer.set_opacity(0.55)
            ctx.scene.add(layer)
        ctx.scene.add(main)

        run_time = float(ctx.duration) if ctx.duration is not None else 0.8
        # Phase 1: fade up the stack.
        ctx.scene.play(
            FadeIn(layer_cyan),
            FadeIn(layer_magenta),
            FadeIn(main),
            run_time=run_time * 0.4,
        )

        # Phase 2: glitch jitter — small x-axis shifts on the main layer,
        # number of jitter frames scaled by intensity.
        rng = np.random.default_rng()
        jitter_frames = max(2, int(6 * config.glitch_intensity))
        jitter_amp = 0.04 + 0.10 * config.glitch_intensity
        for _ in range(jitter_frames):
            dx = rng.uniform(-jitter_amp, jitter_amp)
            ctx.scene.play(main.animate.shift([dx, 0, 0]), run_time=0.04)
            ctx.scene.play(main.animate.shift([-dx, 0, 0]), run_time=0.04)

        # Phase 3: fade out the aberration so we settle on a clean main layer.
        ctx.scene.play(
            FadeOut(layer_cyan), FadeOut(layer_magenta),
            run_time=run_time * 0.2,
        )
