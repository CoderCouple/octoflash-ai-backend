"""kinetic_text — words dance with independent size/position per beat."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class KineticTextConfig(BaseModel):
    text: str  # space-separated; each word animates independently
    color: str = "#FFFFFF"
    base_size: float = 64.0
    beat_seconds: float = Field(default=0.25, gt=0.0)
    scale_variance: float = Field(default=0.4, ge=0.0, le=2.0)
    position_jitter: float = Field(default=0.2, ge=0.0, le=1.0)


@register
class KineticTextPrimitive(Primitive):
    PRIMITIVE_ID = "kinetic_text"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = KineticTextConfig
    IMPLEMENTED = True

    def build(self, config: KineticTextConfig, ctx: PrimitiveContext) -> None:
        import numpy as np
        from manim import FadeIn, ORIGIN, RIGHT, Text, VGroup

        words = [w for w in config.text.split() if w]
        if not words:
            return

        # Each word is its own mobject so we can animate them independently.
        word_mobs = [
            Text(w, color=config.color, font_size=config.base_size)
            for w in words
        ]
        row = VGroup(*word_mobs).arrange(RIGHT, buff=0.35).move_to(ORIGIN)
        ctx.scene.add(row)

        run_time = float(ctx.duration) if ctx.duration is not None else 3.0
        # Reveal first beat.
        ctx.scene.play(FadeIn(row, shift=ORIGIN), run_time=min(0.4, run_time * 0.2))

        # Remaining time fills with per-beat jittered scale+position.
        remaining = max(run_time - 0.4, config.beat_seconds * 2)
        n_beats = max(1, int(remaining / max(config.beat_seconds, 0.05)))
        rng = np.random.default_rng()

        # Anchor positions so we can spring back instead of drifting.
        anchors = [w.get_center().copy() for w in word_mobs]

        for _ in range(n_beats):
            anims = []
            for w, anchor in zip(word_mobs, anchors):
                # Random scale within (1 - variance, 1 + variance).
                target_scale = 1.0 + rng.uniform(
                    -config.scale_variance, config.scale_variance
                )
                # Random small position offset.
                dx = rng.uniform(-config.position_jitter, config.position_jitter)
                dy = rng.uniform(-config.position_jitter, config.position_jitter)
                anims.append(
                    w.animate.scale(target_scale / w.height * w.height).move_to(
                        anchor + np.array([dx, dy, 0.0])
                    )
                )
            ctx.scene.play(*anims, run_time=config.beat_seconds * 0.5)
            # Spring back to baseline for the second half of the beat.
            spring_anims = [
                w.animate.move_to(anchor) for w, anchor in zip(word_mobs, anchors)
            ]
            ctx.scene.play(*spring_anims, run_time=config.beat_seconds * 0.5)
