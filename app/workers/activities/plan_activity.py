"""
Plan activity — Claude segments a Project's brief into N clip-briefs.

Wraps ClipPlannerService. One Claude call per project. Output is the list of
PlannedClip dicts; the workflow then calls create_scenes_activity to persist
them as Scene rows.
"""

from __future__ import annotations

from dataclasses import dataclass

from temporalio import activity

import app.model  # noqa: F401
from app.service.clip_planner_service import ClipPlannerService


@dataclass
class PlanClipsInput:
    project_id: str
    transcript: str
    description: str
    manim_prompt: str
    target_duration: float
    orientation: str = "portrait"
    max_clips: int = 8


@dataclass
class PlannedClipDict:
    n: int
    title: str
    prompt: str
    duration: float


@dataclass
class PlanClipsOutput:
    clips: list[PlannedClipDict]


@activity.defn(name="plan_clips")
async def plan_clips_activity(payload: PlanClipsInput) -> PlanClipsOutput:
    activity.logger.info(
        "plan_clips: project=%s target=%.0fs orient=%s max_clips=%d",
        payload.project_id, payload.target_duration, payload.orientation, payload.max_clips,
    )

    planned = await ClipPlannerService().plan(
        transcript=payload.transcript,
        description=payload.description,
        manim_prompt=payload.manim_prompt,
        target_duration=payload.target_duration,
        orientation=payload.orientation,
        max_clips=payload.max_clips,
    )

    clips = [
        PlannedClipDict(n=p.n, title=p.title, prompt=p.prompt, duration=p.duration)
        for p in planned
    ]
    activity.logger.info("plan_clips: produced %d clips", len(clips))
    return PlanClipsOutput(clips=clips)
