"""
GenerateVariationsWorkflow — render N variations of a scene in parallel.

This is the reference workflow showing Temporal's value for octoflash:
- N renders kick off concurrently via asyncio.gather over execute_activity.
- Each render's retries / timeouts / heartbeats are owned by Temporal.
- The Job row gets progress updates as each variation completes.
- If a worker crashes mid-render, Temporal reschedules on a healthy worker —
  no state loss, no manual reaper.

Workflows must be deterministic: no clock, no random, no IO. All IO happens
inside activities. Time and IDs come from `workflow.now()` and `workflow.uuid4()`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

# Activity imports inside the workflow's deterministic sandbox.
with workflow.unsafe.imports_passed_through():
    from app.workers.activities.db_activity import (
        InsertVariationInput,
        UpdateJobInput,
        insert_variation_activity,
        update_job_activity,
    )
    from app.workers.activities.render_activity import (
        RenderVariationInput,
        RenderVariationOutput,
        render_variation_activity,
    )
    from app.workers.activities.storage_activity import (
        UploadRenderInput,
        upload_render_activity,
    )


_RENDER_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)
_DB_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=5,
)


@dataclass
class GenerateVariationsInput:
    job_id: str
    scene_id: str
    template_id: str
    params: dict[str, Any]
    style: str | None
    extra_steps: list[dict[str, Any]] = field(default_factory=list)
    n: int = 4
    seed: int | None = None


@dataclass
class RerenderVariationInput:
    job_id: str
    variation_id: str
    scene_id: str
    template_id: str
    params: dict[str, Any]
    style: str | None
    extra_steps: list[dict[str, Any]] = field(default_factory=list)
    seed: int | None = None


async def _mark_job_failed(job_id: str, exc: BaseException) -> None:
    """Best-effort terminal-state update so /jobs/{id} reflects reality.

    Called from a workflow's except block. Failures here are swallowed
    (logged only) because raising would mask the original exception.
    """
    try:
        await workflow.execute_activity(
            update_job_activity,
            UpdateJobInput(
                job_id=job_id,
                status="failed",
                finished_at=workflow.now(),
                log_entry={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)[:500],
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
    except Exception:
        workflow.logger.exception(
            "Cleanup update_job_activity failed for job %s — Job row will stay running.",
            job_id,
        )


@workflow.defn
class GenerateVariationsWorkflow:
    """Fan out N renders for one scene, upload each, insert Variation rows."""

    @workflow.run
    async def run(self, input: GenerateVariationsInput) -> list[str]:
        info = workflow.info()
        await workflow.execute_activity(
            update_job_activity,
            UpdateJobInput(
                job_id=input.job_id,
                status="running",
                progress=0,
                started_at=workflow.now(),
                workflow_id=info.workflow_id,
                run_id=info.run_id,
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        async def render_and_upload(i: int) -> str:
            render: RenderVariationOutput = await workflow.execute_activity(
                render_variation_activity,
                RenderVariationInput(
                    scene_id=input.scene_id,
                    variation_index=i,
                    template_id=input.template_id,
                    params=input.params,
                    style=input.style,
                    extra_steps=input.extra_steps,
                    quality="preview",
                    seed=(input.seed + i) if input.seed is not None else None,
                ),
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=_RENDER_RETRY,
            )
            object_key = f"scenes/{input.scene_id}/v{i}-{workflow.uuid4()}.mp4"
            video_url = await workflow.execute_activity(
                upload_render_activity,
                UploadRenderInput(local_path=render.local_path, key=object_key),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RENDER_RETRY,
            )
            variation_id: str = await workflow.execute_activity(
                insert_variation_activity,
                InsertVariationInput(
                    scene_id=input.scene_id,
                    params_snapshot=render.snapshot,
                    video_url=video_url,
                    audio_url=None,
                    duration=render.duration,
                    frame_count=render.frame_count,
                    file_size=render.file_size,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )
            return variation_id

        try:
            # Parallel fan-out — this is the line Temporal was built for.
            variation_ids: list[str] = await asyncio.gather(
                *[render_and_upload(i) for i in range(input.n)]
            )
        except Exception as e:
            await _mark_job_failed(input.job_id, e)
            raise

        await workflow.execute_activity(
            update_job_activity,
            UpdateJobInput(
                job_id=input.job_id,
                status="done",
                progress=100,
                finished_at=workflow.now(),
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
        return variation_ids


@workflow.defn
class RerenderVariationWorkflow:
    """Re-render a single existing Variation (optionally with overridden params)."""

    @workflow.run
    async def run(self, input: RerenderVariationInput) -> str:
        # TODO: hydrate Variation, render once, upload, update Variation row (not insert).
        raise NotImplementedError("Rerender workflow body pending")
