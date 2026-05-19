"""Run Manim for one variation. Returns metadata about the produced MP4."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from temporalio import activity


@dataclass
class RenderVariationInput:
    scene_id: str
    variation_index: int  # 0..n-1 within the parent generate-variations call
    template_id: str
    params: dict[str, Any]
    style: str | None
    extra_steps: list[dict[str, Any]]
    quality: str  # "preview" | "export"
    seed: int | None


@dataclass
class RenderVariationOutput:
    local_path: str
    duration: float
    frame_count: int
    file_size: int
    snapshot: dict[str, Any]


@activity.defn(name="render_variation")
async def render_variation_activity(
    payload: RenderVariationInput,
) -> RenderVariationOutput:
    """Hand off to ManimRunnerService.render(). Heavy + blocking — runs in a thread."""
    activity.heartbeat({"phase": "manim_start", "variation_index": payload.variation_index})

    # Lazy import keeps Manim out of the worker process's hot path until needed.
    from app.service.manim_runner_service import ManimRunnerService

    runner = ManimRunnerService()
    # Manim is sync + CPU-bound. asyncio.to_thread lets the Temporal worker
    # keep heartbeats flowing on other coroutines while the render runs.
    result = await asyncio.to_thread(
        runner.render,
        payload.template_id,
        payload.params,
        payload.style,
        payload.extra_steps,
        payload.quality,
        payload.seed,
    )

    activity.heartbeat({"phase": "manim_done", "variation_index": payload.variation_index})

    return RenderVariationOutput(
        local_path=result.video_path,
        duration=result.duration,
        frame_count=result.frame_count,
        file_size=result.file_size,
        snapshot=result.snapshot,
    )
