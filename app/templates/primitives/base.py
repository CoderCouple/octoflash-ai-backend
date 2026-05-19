"""
Primitive — the reusable layer underneath templates.

A primitive is a small, parameterized animation atom (text_reveal, fade_swap,
callout_zoom, chart_bar_grow, …). Templates compose primitives by referencing
them via PRIMITIVE_ID and binding configs in YAML-like fashion (but in Pydantic).

Versioning:
  PRIMITIVE_VERSION is recorded in every render's audit snapshot. Bump on
  behavior changes so old Variations can tell exactly which primitive
  implementation produced them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel


class PrimitiveContext:
    """Passed into `Primitive.build()` — the scene + timing + style env."""

    def __init__(
        self,
        scene: Any,
        t: float,
        duration: float | None,
        style: str | None,
    ) -> None:
        self.scene = scene
        self.t = t
        self.duration = duration
        self.style = style


class Primitive(ABC):
    """ABC for all reusable render primitives."""

    PRIMITIVE_ID: ClassVar[str]
    PRIMITIVE_VERSION: ClassVar[str] = "1.0.0"
    CONFIG_SCHEMA: ClassVar[type[BaseModel]]

    # Opt-in flag: True once the Manim `build()` is wired (i.e. no longer raises
    # NotImplementedError). The planner's catalog block only surfaces templates
    # whose every referenced primitive has IMPLEMENTED=True, so Claude can't
    # propose unrenderable templates. Default is False so new stubs never
    # accidentally claim implementation.
    IMPLEMENTED: ClassVar[bool] = False

    @classmethod
    def parse_config(cls, raw: dict[str, Any]) -> BaseModel:
        """Validate the raw bound config against this primitive's schema."""
        return cls.CONFIG_SCHEMA(**raw)

    @abstractmethod
    def build(self, config: BaseModel, ctx: PrimitiveContext) -> None:
        """Add animations to `ctx.scene` given the resolved config."""
        raise NotImplementedError
