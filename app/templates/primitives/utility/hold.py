"""
hold — wait `duration` seconds without changing the scene.

The simplest possible primitive — used by virtually every template to dwell
on a frame between animated steps.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.templates.primitives.base import Primitive, PrimitiveContext
from app.templates.primitives.registry import register


class HoldConfig(BaseModel):
    pass  # No config — duration comes from the StepSpec.


@register
class HoldPrimitive(Primitive):
    PRIMITIVE_ID = "hold"
    PRIMITIVE_VERSION = "1.0.0"
    CONFIG_SCHEMA = HoldConfig
    IMPLEMENTED = True

    def build(self, config: HoldConfig, ctx: PrimitiveContext) -> None:
        wait_for = float(ctx.duration) if ctx.duration is not None else 1.0
        if wait_for > 0:
            ctx.scene.wait(wait_for)
