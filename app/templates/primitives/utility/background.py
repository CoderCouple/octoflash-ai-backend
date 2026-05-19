"""background — solid-color canvas fill. Step 0 of most templates."""

from __future__ import annotations

from pydantic import BaseModel

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class BackgroundConfig(BaseModel):
    color: str = "#000000"


@register
class BackgroundPrimitive(Primitive):
    PRIMITIVE_ID = "background"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = BackgroundConfig
    IMPLEMENTED = True

    def build(self, config: BackgroundConfig, ctx: PrimitiveContext) -> None:
        # Manim's camera holds the background color as a hex string. Setting it
        # once at scene start is enough — later primitives draw on top.
        ctx.scene.camera.background_color = config.color
