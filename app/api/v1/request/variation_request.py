from typing import Any

from pydantic import BaseModel, Field


class RerenderVariationRequest(BaseModel):
    """Re-render an existing variation, optionally with overridden params."""

    params_override: dict[str, Any] | None = Field(
        default=None,
        description="If set, replaces params_snapshot for this re-render.",
    )
