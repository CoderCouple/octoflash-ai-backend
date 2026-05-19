"""redacted_text — black bar covers text, then wipes off to reveal."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class RedactedTextConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 72.0
    redaction_color: str = "#000000"
    wipe_direction: Literal["left_to_right", "right_to_left"] = "left_to_right"


@register
class RedactedTextPrimitive(Primitive):
    PRIMITIVE_ID = "redacted_text"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = RedactedTextConfig
    IMPLEMENTED = True

    def build(self, config: RedactedTextConfig, ctx: PrimitiveContext) -> None:
        from manim import LEFT, RIGHT, Rectangle, Text, ValueTracker

        text = Text(config.text, color=config.color, font_size=config.size)
        # Slight padding around the bbox so the bar fully covers the glyphs.
        pad = 0.1
        bar_w = text.width + pad * 2
        bar_h = text.height + pad * 2
        bar = Rectangle(
            width=bar_w, height=bar_h,
            fill_color=config.redaction_color, fill_opacity=1.0, stroke_width=0,
        )
        bar.move_to(text.get_center())
        ctx.scene.add(text, bar)  # bar drawn over text

        # Wipe: shrink the bar from the wipe_direction edge so the text underneath
        # is revealed progressively. Use a ValueTracker + updater so the bar
        # stays edge-aligned during the shrink.
        edge = LEFT if config.wipe_direction == "left_to_right" else RIGHT
        anchor_x = text.get_critical_point(edge)[0]
        tracker = ValueTracker(1.0)

        def _shrink(rect: Rectangle) -> None:
            new_width = max(bar_w * tracker.get_value(), 0.0001)
            rect.stretch_to_fit_width(new_width)
            # Pin the bar's wipe-side edge to the original anchor.
            if config.wipe_direction == "left_to_right":
                rect.next_to([anchor_x, text.get_center()[1], 0], RIGHT, buff=0).shift(LEFT * 0)
                rect.move_to([anchor_x + new_width / 2, text.get_center()[1], 0])
            else:
                rect.move_to([anchor_x - new_width / 2, text.get_center()[1], 0])

        bar.add_updater(_shrink)
        run_time = float(ctx.duration) if ctx.duration is not None else 0.8
        ctx.scene.play(tracker.animate.set_value(0.0), run_time=run_time)
        bar.clear_updaters()
        ctx.scene.remove(bar)
