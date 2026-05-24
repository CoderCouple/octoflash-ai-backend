"""
GenerateVideoWorkflow — analyzed Project → N per-clip MP4s → stitched final MP4.

Steps:
  1. plan_clips_activity — Claude splits the brief into N atomic clip-briefs
  2. create_scenes_activity — persist N Scene rows (status=draft)
  3. fan out N generate_clip_activity calls in parallel via asyncio.gather
     (return_exceptions=True for failure isolation)
  4. ffmpeg_concat_activity — stitch ready clips into projects/<id>/final_<orient>.mp4
  5. update_project_activity — final_video_url + status=generated

If a single clip fails, the workflow continues with the rest and stitches what's
available. If ALL clips fail, the workflow marks the project failed.
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
    from app.workers.activities.plan_activity import (
        PlanClipsInput,
        PlanClipsOutput,
        plan_clips_activity,
    )
    from app.workers.activities.project_activity import (
        BindScenesToDagInput,
        CreateScenesInput,
        CreateScenesOutput,
        PlannedClipDict,
        UpdateProjectInput,
        bind_scenes_to_dag_activity,
        create_scenes_activity,
        update_project_activity,
    )


_PLAN_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)
_CLIP_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=2,  # one auto-retry then surface to workflow's gather()
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
class GenerateVideoInput:
    execution_id: str
    project_id: str

    # Brief (denormalized so activities don't all need to re-read Project)
    transcript: str
    description: str
    manim_prompt: str
    source_duration: float

    # Render options
    orientation: str = "portrait"
    voiceover: bool = True
    voice_id: str = ""
    quality: str = "ql"
    max_clips: int = 8

    # Source frame paths (relative to STORAGE_DIR) for per-clip vision context
    source_frame_paths: list[str] = field(default_factory=list)


async def _mark_failed(execution_id: str, project_id: str, exc: BaseException) -> None:
    """Best-effort terminal-state write on workflow-level failure."""
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
        await workflow.execute_activity(
            update_project_activity,
            UpdateProjectInput(project_id=project_id, status="failed"),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
    except Exception:
        workflow.logger.exception("cleanup writes failed for project %s", project_id)


@workflow.defn
class GenerateVideoWorkflow:
    @workflow.run
    async def run(self, input: GenerateVideoInput) -> dict:
        info = workflow.info()

        # ── mark running ──
        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=input.execution_id,
                status="RUNNING",
                started_at=workflow.now(),
                temporal_workflow_id=info.workflow_id,
                temporal_run_id=info.run_id,
                log_entry={"step": "started"},
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
        await workflow.execute_activity(
            update_project_activity,
            UpdateProjectInput(project_id=input.project_id, status="generating"),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        try:
            # ── 1. PLAN clips (1 Claude call) ──
            planned: PlanClipsOutput = await workflow.execute_activity(
                plan_clips_activity,
                PlanClipsInput(
                    project_id=input.project_id,
                    transcript=input.transcript,
                    description=input.description,
                    manim_prompt=input.manim_prompt,
                    target_duration=input.source_duration or 60.0,
                    orientation=input.orientation,
                    max_clips=input.max_clips,
                ),
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=_PLAN_RETRY,
            )
            await workflow.execute_activity(
                update_execution_activity,
                UpdateExecutionInput(
                    execution_id=input.execution_id,
                    log_entry={"step": "planned", "clip_count": len(planned.clips)},
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )

            # ── 2. PERSIST as Scene rows (1 DB write) ──
            created: CreateScenesOutput = await workflow.execute_activity(
                create_scenes_activity,
                CreateScenesInput(
                    project_id=input.project_id,
                    orientation=input.orientation,
                    clips=[
                        PlannedClipDict(n=c.n, title=c.title, prompt=c.prompt, duration=c.duration)
                        for c in planned.clips
                    ],
                ),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_DB_RETRY,
            )

            # ── 2b. BIND the new scenes back to the seeded DAG nodes ──
            # Patches data.scene_id on each scene-typed node in
            # workflow.definition so the FE can resolve clicks via the
            # JSONB blob alone, instead of falling back to n-matching.
            # Idempotent (first-bind-wins) so a second orientation's
            # generate doesn't clobber the first.
            await workflow.execute_activity(
                bind_scenes_to_dag_activity,
                BindScenesToDagInput(
                    project_id=input.project_id,
                    orientation=input.orientation,
                    scenes=list(created.scenes),
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )

            # ── 3. FAN OUT per-clip generate in parallel ──
            # asyncio.gather with return_exceptions=True is the failure-isolation
            # pattern: one clip's crash doesn't tank the siblings.
            workflow.logger.info(
                "fanning out %d per-clip generate activities", len(created.scenes),
            )
            clip_tasks = [
                workflow.execute_activity(
                    generate_clip_activity,
                    GenerateClipInput(
                        scene_id=s.scene_id,
                        project_id=input.project_id,
                        n=s.n,
                        title=s.title,
                        clip_prompt=s.prompt,
                        duration=s.duration,
                        transcript=input.transcript,
                        description=input.description,
                        manim_prompt=input.manim_prompt,
                        orientation=input.orientation,
                        voiceover=input.voiceover,
                        voice_id=input.voice_id,
                        quality=input.quality,
                        source_frame_paths=input.source_frame_paths,
                    ),
                    # Single clip: script_gen (~75s) + render (~35s) + eval (~25s) ≈ 2-5 min
                    start_to_close_timeout=timedelta(minutes=15),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_CLIP_RETRY,
                )
                for s in created.scenes
            ]
            clip_results = await asyncio.gather(*clip_tasks, return_exceptions=True)

            successes: list[GenerateClipOutput] = []
            failures = 0
            for s, r in zip(created.scenes, clip_results):
                if isinstance(r, Exception):
                    workflow.logger.error(
                        "clip n=%d (scene=%s) failed: %s", s.n, s.scene_id, str(r)[:300],
                    )
                    failures += 1
                else:
                    successes.append(r)

            await workflow.execute_activity(
                update_execution_activity,
                UpdateExecutionInput(
                    execution_id=input.execution_id,
                    log_entry={
                        "step": "clips_rendered",
                        "ok": len(successes),
                        "failed": failures,
                        "cached_hits": sum(1 for r in successes if r.cached),
                    },
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )

            if not successes:
                raise RuntimeError(
                    f"All {len(created.scenes)} per-clip renders failed — see Job logs"
                )

            # Sort successes back into clip order (gather preserves order but be defensive)
            ordered = sorted(
                successes,
                key=lambda r: next(s.n for s in created.scenes if s.scene_id == r.scene_id),
            )

            # ── 4. FFMPEG CONCAT ──
            stitched: FFmpegConcatOutput = await workflow.execute_activity(
                ffmpeg_concat_activity,
                FFmpegConcatInput(
                    project_id=input.project_id,
                    clip_paths=[r.video_file for r in ordered],
                    orientation=input.orientation,
                ),
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=_FFMPEG_RETRY,
            )

            # ── 5. PERSIST final video onto Project + mark generated ──
            # Route to the orientation-specific column so a dual-orientation
            # run leaves both `final_portrait_video_url` and
            # `final_landscape_video_url` set independently.
            project_patch = UpdateProjectInput(
                project_id=input.project_id,
                status="generated",
            )
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
            await _mark_failed(input.execution_id, input.project_id, e)
            raise

        # ── done ──
        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=input.execution_id,
                status="COMPLETED",
                completed_at=workflow.now(),
                log_entry={
                    "step": "done",
                    "clip_count": len(ordered),
                    "final_video": stitched.output_path,
                    "final_size_bytes": stitched.size_bytes,
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        return {
            "final_video_url": stitched.output_path,
            "clip_count": len(ordered),
            "clip_failures": failures,
            "size_bytes": stitched.size_bytes,
        }
