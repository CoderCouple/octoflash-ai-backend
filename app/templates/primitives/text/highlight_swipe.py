"""highlight_swipe — colored marker swipes across a substring of text."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class HighlightSwipeConfig(BaseModel):
    text: str
    highlight_substring: str  # must occur in `text`; raises if missing
    color: str = "#FFFFFF"
    highlight_color: str = "#FFD400"  # marker color (semi-transparent at render time)
    size: float = 64.0
    swipe_seconds: float = Field(default=0.4, gt=0.0)


@register
class HighlightSwipePrimitive(Primitive):
    PRIMITIVE_ID = "highlight_swipe"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = HighlightSwipeConfig
    IMPLEMENTED = True

    def build(self, config: HighlightSwipeConfig, ctx: PrimitiveContext) -> None:
        from manim import LEFT, RIGHT, Rectangle, Text, ValueTracker

        text = Text(config.text, color=config.color, font_size=config.size)
        ctx.scene.add(text)

        # Locate the substring inside the rendered text by character index range.
        idx = config.text.find(config.highlight_substring)
        if idx < 0:
            # Substring not found — silently degrade by highlighting the entire
            # text so the render still produces something sensible.
            sub_chars = list(text)
        else:
            sub_chars = list(text)[idx : idx + len(config.highlight_substring)]
        if not sub_chars:
            return

        # Compute the substring's bbox from its constituent character mobjects.
        left = min(c.get_critical_point(LEFT)[0] for c in sub_chars)
        right = max(c.get_critical_point(RIGHT)[0] for c in sub_chars)
        full_w = right - left
        y = text.get_center()[1]
        height = text.height * 0.95

        bar = Rectangle(
            width=0.0001, height=height,
            fill_color=config.highlight_color, fill_opacity=0.5, stroke_width=0,
        )
        # Hide drawing behind text so the marker reads like a real highlighter.
        bar.set_z_index(-1)
        bar.move_to([left, y, 0])
        ctx.scene.add(bar)

        tracker = ValueTracker(0.0)

        def _grow(rect: Rectangle) -> None:
            w = max(full_w * tracker.get_value(), 0.0001)
            rect.stretch_to_fit_width(w)
            rect.move_to([left + w / 2, y, 0])

        bar.add_updater(_grow)
        run_time = float(ctx.duration) if ctx.duration is not None else config.swipe_seconds
        ctx.scene.play(tracker.animate.set_value(1.0), run_time=run_time)
        bar.clear_updaters()
