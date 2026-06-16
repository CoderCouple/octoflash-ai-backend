"""
AnalyzeProjectWorkflow — source URL → editable brief on the Project row.

Runs once per project. Steps:
  1. update_project_status_activity → status=analyzing
  2. analyze_source_activity → transcript + description + manim_prompt + frames
  3. update_project_activity → persist all of the above + status=analyzed
  4. update_execution_activity → mark Job done

After this the user can edit the brief in the UI, then trigger
GenerateVideoWorkflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workers.activities.analyze_activity import (
        AnalyzeSourceInput,
        AnalyzeSourceOutput,
        analyze_source_activity,
    )
    from app.workers.activities.db_activity import (
        UpdateExecutionInput,
        update_execution_activity,
    )
    from app.workers.activities.plan_activity import (
        PlanClipsInput,
        PlanClipsOutput,
        plan_clips_activity,
    )
    from app.workers.activities.project_activity import (
        UpdateProjectInput,
        update_project_activity,
    )
    from app.workers.activities.seed_workflow_activity import (
        SeedClip,
        SeedWorkflowInput,
        seed_workflow_definition_activity,
    )


_ANALYZE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
    backoff_coefficient=2.0,
)
_DB_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=5,
)


_PLAN_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_attempts=2,
    backoff_coefficient=2.0,
)


@dataclass
class AnalyzeProjectInput:
    execution_id: str
    workflow_id: str
    project_id: str
    source_url: str
    title_was_unset: bool = True  # if True, overwrite Project.title with title_hint
    max_clips: int = 8
    # Owner — forwarded to AnalyzeSourceInput so the activity can pull
    # the user's YouTube cookies from the credential vault and feed them
    # to yt-dlp. Without this, YouTube IP-blocks data-center scrapers.
    user_id: str | None = None


async def _mark_job_failed(execution_id: str, exc: BaseException) -> None:
    """Best-effort failure write so /jobs/{id} reflects reality."""
    try:
        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=execution_id,
                status="FAILED",
                completed_at=workflow.now(),
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
            "cleanup update_job failed for %s — Job row may stay 'running'", execution_id,
        )


@workflow.defn
class AnalyzeProjectWorkflow:
    @workflow.run
    async def run(self, input: AnalyzeProjectInput) -> dict:
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
                log_entry={"step": "started", "source_url": input.source_url},
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
        await workflow.execute_activity(
            update_project_activity,
            UpdateProjectInput(project_id=input.project_id, status="analyzing"),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        try:
            # ── analyze (heavy: download + frames + transcript + describe) ──
            result: AnalyzeSourceOutput = await workflow.execute_activity(
                analyze_source_activity,
                AnalyzeSourceInput(
                    project_id=input.project_id,
                    source_url=input.source_url,
                    user_id=input.user_id,
                ),
                # Whisper fallback on a long video can take minutes; allow 20.
                start_to_close_timeout=timedelta(minutes=20),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=_ANALYZE_RETRY,
            )
            await workflow.execute_activity(
                update_execution_activity,
                UpdateExecutionInput(
                    execution_id=input.execution_id,
                    log_entry={
                        "step": "analyzed",
                        "transcript_chars": len(result.transcript),
                        "description_chars": len(result.description),
                        "frame_count": result.frame_count,
                        "transcript_source": result.transcript_source,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )

            # ── persist brief onto Project, mark analyzed ──
            title_update = result.title_hint if (input.title_was_unset and result.title_hint) else None
            await workflow.execute_activity(
                update_project_activity,
                UpdateProjectInput(
                    project_id=input.project_id,
                    status="analyzed",
                    title=title_update,
                    transcript=result.transcript,
                    description=result.description,
                    manim_prompt=result.manim_prompt,
                    source_duration=result.source_duration,
                    frames_dir=result.frames_dir,
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )

            # ── plan clips so the seeded DAG has a real scene chain ──
            # Portrait by default; user can re-plan for landscape at Generate
            # time. target_duration falls back to 60s if the source has no
            # measurable duration (article / text intake).
            planned: PlanClipsOutput = await workflow.execute_activity(
                plan_clips_activity,
                PlanClipsInput(
                    project_id=input.project_id,
                    transcript=result.transcript,
                    description=result.description,
                    manim_prompt=result.manim_prompt,
                    target_duration=result.source_duration or 60.0,
                    orientation="portrait",
                    max_clips=input.max_clips,
                ),
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=_PLAN_RETRY,
            )

            # ── seed the React Flow DAG so the editor opens to a real graph ──
            await workflow.execute_activity(
                seed_workflow_definition_activity,
                SeedWorkflowInput(
                    workflow_id=input.workflow_id,
                    source_url=input.source_url,
                    clips=[
                        SeedClip(n=c.n, title=c.title, prompt=c.prompt, duration=c.duration)
                        for c in planned.clips
                    ],
                ),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_DB_RETRY,
            )
            await workflow.execute_activity(
                update_execution_activity,
                UpdateExecutionInput(
                    execution_id=input.execution_id,
                    log_entry={"step": "seeded_dag", "clip_count": len(planned.clips)},
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )
        except Exception as e:
            await _mark_job_failed(input.execution_id, e)
            await workflow.execute_activity(
                update_project_activity,
                UpdateProjectInput(project_id=input.project_id, status="failed"),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )
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
                    "title_hint": result.title_hint,
                    "source_duration": result.source_duration,
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        return {
            "title_hint": result.title_hint,
            "source_duration": result.source_duration,
            "transcript_chars": len(result.transcript),
            "frame_count": result.frame_count,
        }
