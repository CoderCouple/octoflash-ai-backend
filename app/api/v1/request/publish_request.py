"""Request body for POST /api/v1/targets/{id}/publish."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PublishTargetRequest(BaseModel):
    """One project's final render published to one Target."""

    project_id: str
    orientation: Literal["portrait", "landscape"] = "portrait"
    title: str = Field(..., min_length=1, max_length=150)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    # YouTube: 'public' | 'unlisted' | 'private'. Other platforms ignore or
    # remap. Default 'private' so an accidental publish doesn't go live.
    privacy: str = "private"
    # Platform-specific extras. Examples:
    #   YouTube: {"categoryId": "27"}      (27 = Education)
    #   Instagram: {"caption": "…"}
    extra: dict[str, Any] = Field(default_factory=dict)
