"""
Two response shapes:

  TemplateSummaryResponse  → returned by GET /templates (the library list).
                             Lightweight: id/name/category/glyph/manic/implemented.
  TemplateDetailResponse   → returned by GET /templates/{id}.
                             Full TemplateDefinition (params + steps + style_modifiers).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class TemplateSummaryResponse(BaseModel):
    """One row in the template library — what `GET /templates` returns."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: str
    glyph: str
    manic_compatible: bool
    implemented: bool  # True if a defs/<id>.py exists with a valid TEMPLATE export


class TemplateDetailResponse(BaseModel):
    """Full template spec — what `GET /templates/{id}` returns.

    Mirrors TemplateDefinition closely but accepts plain dicts for the
    nested shapes so we can serialize whatever the def declares without
    re-deriving the discriminated unions on the response side.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    name: str
    category: str
    glyph: str
    manic_compatible: bool
    description: str | None = None
    params: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    style_modifiers: dict[str, dict[str, Any]]
    default_duration: float
    default_size: tuple[int, int]
    content_hash: str
