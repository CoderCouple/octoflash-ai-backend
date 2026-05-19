from typing import Any

from pydantic import BaseModel, Field


class CreateSceneRequest(BaseModel):
    template: str = Field(..., min_length=1, max_length=64)
    title: str | None = Field(default=None, max_length=255)
    prompt: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    duration: float | None = None
    style: str | None = None
    motion: str | None = None
    n: int | None = None  # explicit ordering; defaults to next slot


class UpdateSceneRequest(BaseModel):
    title: str | None = None
    template: str | None = None
    prompt: str | None = None
    params: dict[str, Any] | None = None
    duration: float | None = None
    style: str | None = None
    motion: str | None = None


class GenerateVariationsRequest(BaseModel):
    n: int = Field(default=4, ge=1, le=12)
    seed: int | None = None  # optional deterministic seeding


class SelectVariationRequest(BaseModel):
    variation_id: str
