"""lower_third_strip — name/title strip animates in from a corner."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class LowerThirdStripConfig(BaseModel):
    name: str
    title: str = ""
    accent_color: str = "#FF6B35"
    text_color: str = "#FFFFFF"
    bar_color: str = "#0A0A0A"
    corner: Literal["bottom_left", "bottom_right"] = "bottom_left"
    enter_seconds: float = 0.5


@register
class LowerThirdStripPrimitive(Primitive):
    PRIMITIVE_ID = "lower_third_strip"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = LowerThirdStripConfig
    IMPLEMENTED = True

    def build(self, config: LowerThirdStripConfig, ctx: PrimitiveContext) -> None:
        from manim import (
            DOWN, LEFT, RIGHT, DL, DR, Rectangle, Text, VGroup, rate_functions,
        )

        # Strip dimensions (in Manim units).
        bar_w, bar_h = 5.5, 1.2
        accent_w = 0.15

        bar = Rectangle(width=bar_w, height=bar_h, fill_color=config.bar_color,
                        fill_opacity=0.92, stroke_width=0)
        accent = Rectangle(width=accent_w, height=bar_h, fill_color=config.accent_color,
                           fill_opacity=1.0, stroke_width=0)
        # Put accent stripe at the bar's leading edge.
        accent.next_to(bar, LEFT, buff=0).shift(RIGHT * accent_w)

        name = Text(config.name, color=config.text_color, font_size=44)
        title = Text(config.title, color=config.text_color, font_size=26) if config.title else None

        text_group = VGroup(name, title) if title else VGroup(name)
        text_group.arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        text_group.next_to(accent, RIGHT, buff=0.4).align_to(bar, DOWN).shift([0, 0.15, 0])

        group = VGroup(bar, accent, text_group)

        # Anchor at bottom corner, then start off-screen for the slide-in.
        if config.corner == "bottom_left":
            group.to_corner(DL, buff=0.5)
            offset = LEFT * (bar_w + 1.5)
        else:
            group.to_corner(DR, buff=0.5)
            offset = RIGHT * (bar_w + 1.5)
        group.shift(offset)
        ctx.scene.add(group)

        enter = config.enter_seconds
        total = float(ctx.duration) if ctx.duration is not None else 3.0
        hold = max(0.0, total - 2 * enter)

        ctx.scene.play(group.animate.shift(-offset), run_time=enter,
                       rate_func=rate_functions.ease_out_cubic)
        if hold > 0:
            ctx.scene.wait(hold)
        ctx.scene.play(group.animate.shift(offset), run_time=enter,
                       rate_func=rate_functions.ease_in_cubic)
