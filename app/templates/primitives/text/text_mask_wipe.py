"""text_mask_wipe — text revealed by a sweeping bar mask."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class TextMaskWipeConfig(BaseModel):
    text: str
    color: str = "#FFFFFF"
    size: float = 72.0
    mask_color: str = "#FFFFFF"
    sweep: Literal["left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"] = (
        "left_to_right"
    )


@register
class TextMaskWipePrimitive(Primitive):
    PRIMITIVE_ID = "text_mask_wipe"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = TextMaskWipeConfig
    IMPLEMENTED = True

    def build(self, config: TextMaskWipeConfig, ctx: PrimitiveContext) -> None:
        from manim import DOWN, LEFT, RIGHT, Rectangle, Text, UP, ValueTracker

        text = Text(config.text, color=config.color, font_size=config.size)
        pad = 0.1
        bar_w = text.width + pad * 2
        bar_h = text.height + pad * 2
        bar = Rectangle(
            width=bar_w, height=bar_h,
            fill_color=config.mask_color, fill_opacity=1.0, stroke_width=0,
        )
        bar.move_to(text.get_center())
        ctx.scene.add(text, bar)

        # 4-directional sweep. ValueTracker drives the bar's shrink along the
        # sweep axis; an updater pins the bar's leading edge so the un-covered
        # portion of the text reveals progressively.
        cx, cy = text.get_center()[0], text.get_center()[1]
        horizontal = config.sweep in ("left_to_right", "right_to_left")
        forward = config.sweep in ("left_to_right", "top_to_bottom")
        tracker = ValueTracker(1.0)

        if horizontal:
            anchor_x = text.get_critical_point(LEFT if forward else RIGHT)[0]
        else:
            anchor_y = text.get_critical_point(UP if forward else DOWN)[1]

        def _shrink(rect: Rectangle) -> None:
            t = tracker.get_value()
            if horizontal:
                new_w = max(bar_w * t, 0.0001)
                rect.stretch_to_fit_width(new_w)
                if forward:
                    rect.move_to([anchor_x + new_w / 2, cy, 0])  # pin LEFT edge
                else:
                    rect.move_to([anchor_x - new_w / 2, cy, 0])  # pin RIGHT edge
            else:
                new_h = max(bar_h * t, 0.0001)
                rect.stretch_to_fit_height(new_h)
                if forward:
                    rect.move_to([cx, anchor_y - new_h / 2, 0])  # pin TOP edge
                else:
                    rect.move_to([cx, anchor_y + new_h / 2, 0])  # pin BOTTOM edge

        bar.add_updater(_shrink)
        run_time = float(ctx.duration) if ctx.duration is not None else 0.7
        ctx.scene.play(tracker.animate.set_value(0.0), run_time=run_time)
        bar.clear_updaters()
        ctx.scene.remove(bar)
