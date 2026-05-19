from pydantic import BaseModel, Field


class PlanFromPromptRequest(BaseModel):
    """Plan an ordered set of scenes from a freeform user prompt."""

    prompt: str = Field(..., min_length=1, max_length=4000)

    # Soft hints — planner can deviate when the prompt calls for it.
    style_preference: str | None = Field(
        default=None,
        description="One of: editorial, manic, classic_3b1b, kurzgesagt, whiteboard, neon, mono.",
    )
    max_scenes: int | None = Field(default=None, ge=1, le=30)
    target_duration: float | None = Field(
        default=None, ge=1.0, le=600.0,
        description="Soft target total duration in seconds (sum of per-scene durations).",
    )
