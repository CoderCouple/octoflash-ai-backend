"""
RegenerateClipWorkflow — re-render one clip + auto-stitch the final video.

The editor's per-clip-edit flow:
  1. User edits clip 3's prompt via `PATCH /scenes/{id}` (sync, just updates DB)
  2. User clicks "regenerate" → `POST /scenes/{id}/regenerate` starts THIS workflow
  3. Only clip 3 re-runs script_gen + render
  4. ffmpeg concat re-runs (fast, ~3s with -c copy) so Project.final_video_url
     reflects the new version end-to-end
  5. FE polls /jobs/{id} and refreshes the player when status=done

The other clips' Scene.script_code_hash hasn't changed, so render_clip's
skip-if-unchanged guard makes them no-ops — only the edited clip pays the
script_gen + render cost. The concat is whole-video but cheap.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workers.activities.db_activity import (
        UpdateExecutionInput,
        update_execution_activity,
    )
    from app.workers.activities.ffmpeg_concat_activity import (
        FFmpegConcatInput,
        FFmpegConcatOutput,
        ffmpeg_concat_activity,
    )
    from app.workers.activities.generate_clip_activity import (
        GenerateClipInput,
        GenerateClipOutput,
        generate_clip_activity,
    )
    from app.workers.activities.project_activity import (
        UpdateProjectInput,
        update_project_activity,
    )


_CLIP_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=2,
    backoff_coefficient=2.0,
)
_DB_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=5,
)
_FFMPEG_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_attempts=3,
)


@dataclass
class RegenerateClipInput:
    execution_id: str
    project_id: str

    # The single clip to regen (caller pulled these from DB at request time)
    scene_id: str
    n: int
    title: str
    clip_prompt: str
    duration: float

    # Project-level context (denormalized for the activity)
    transcript: str
    description: str
    manim_prompt: str
    orientation: str
    voiceover: bool
    voice_id: str
    quality: str = "ql"

    # All clips in render order — needed by the concat step. Each entry is the
    # video_url path; the just-regenerated clip's entry will be overwritten with
    # the new render's path before concat fires.
    all_clip_paths_in_order: list[str] = field(default_factory=list)

    source_frame_paths: list[str] = field(default_factory=list)


async def _mark_failed(execution_id: str, exc: BaseException) -> None:
    try:
        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=execution_id,
                status="FAILED",
                completed_at=workflow.now(),
                log_entry={"error_type": type(exc).__name__, "error_message": str(exc)[:500]},
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
    except Exception:
        workflow.logger.exception("regen cleanup write failed for job %s", execution_id)


@workflow.defn
class RegenerateClipWorkflow:
    @workflow.run
    async def run(self, input: RegenerateClipInput) -> dict:
        info = workflow.info()

        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=input.execution_id,
                status="RUNNING",
                started_at=workflow.now(),
                temporal_workflow_id=info.workflow_id,
                temporal_run_id=info.run_id,
                log_entry={"step": "started", "scene_id": input.scene_id, "n": input.n},
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        try:
            # 1. Regen this one clip (skip-if-unchanged still applies inside)
            result: GenerateClipOutput = await workflow.execute_activity(
                generate_clip_activity,
                GenerateClipInput(
                    scene_id=input.scene_id,
                    project_id=input.project_id,
                    n=input.n,
                    title=input.title,
                    clip_prompt=input.clip_prompt,
                    duration=input.duration,
                    transcript=input.transcript,
                    description=input.description,
                    manim_prompt=input.manim_prompt,
                    orientation=input.orientation,
                    voiceover=input.voiceover,
                    voice_id=input.voice_id,
                    quality=input.quality,
                    source_frame_paths=input.source_frame_paths,
                ),
                start_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=_CLIP_RETRY,
            )
            await workflow.execute_activity(
                update_execution_activity,
                UpdateExecutionInput(
                    execution_id=input.execution_id,
                    log_entry={
                        "step": "clip_rendered",
                        "scene_id": input.scene_id,
                        "render_method": result.render_method,
                        "cached": result.cached,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )

            # 2. Replace the just-regenerated clip's path in the ordered list,
            # then re-concat. Indices are 0-based; clip n=1 is at index 0.
            updated_paths = list(input.all_clip_paths_in_order)
            target_idx = input.n - 1
            if 0 <= target_idx < len(updated_paths):
                updated_paths[target_idx] = result.video_file
            else:
                workflow.logger.warning(
                    "regen: n=%d is out of range for clip list (len=%d); "
                    "appending instead", input.n, len(updated_paths),
                )
                updated_paths.append(result.video_file)

            stitched: FFmpegConcatOutput = await workflow.execute_activity(
                ffmpeg_concat_activity,
                FFmpegConcatInput(
                    project_id=input.project_id,
                    clip_paths=updated_paths,
                    orientation=input.orientation,
                ),
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=_FFMPEG_RETRY,
            )

            # 3. Write the new final_video_url onto the orientation-specific column
            project_patch = UpdateProjectInput(project_id=input.project_id)
            if input.orientation == "landscape":
                project_patch.final_landscape_video_url = stitched.output_path
            else:
                project_patch.final_portrait_video_url = stitched.output_path
            await workflow.execute_activity(
                update_project_activity,
                project_patch,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )
        except Exception as e:
            await _mark_failed(input.execution_id, e)
            raise

        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=input.execution_id,
                status="COMPLETED",
                completed_at=workflow.now(),
                log_entry={
                    "step": "done",
                    "scene_id": input.scene_id,
                    "final_video": stitched.output_path,
                    "final_size_bytes": stitched.size_bytes,
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        return {
            "scene_id": input.scene_id,
            "video_file": result.video_file,
            "final_video_url": stitched.output_path,
            "cached": result.cached,
        }
