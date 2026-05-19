"""
Preview + Export workflows — collect each scene's selected variation, stitch.

Preview = low-quality concat-demuxer copy (fast, in-editor playback).
Export  = full-quality libx264 reencode (final deliverable).

Sequential by nature: resolve clips → concat → upload → done. No fan-out.
Per-scene selection rules + URL→path translation live in the resolve activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.settings import settings
    from app.workers.activities.clip_resolve_activity import (
        ResolveProjectClipsInput,
        ResolveProjectClipsOutput,
        resolve_project_clips_activity,
    )
    from app.workers.activities.db_activity import (
        UpdateJobInput,
        update_job_activity,
    )
    from app.workers.activities.ffmpeg_activity import (
        ConcatClipsInput,
        ConcatClipsOutput,
        concat_clips_activity,
    )
    from app.workers.activities.storage_activity import (
        UploadRenderInput,
        upload_render_activity,
    )


_DB_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_attempts=5,
)
_FFMPEG_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_attempts=2,  # ffmpeg failures are usually deterministic — don't loop
)
_UPLOAD_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_attempts=3,
)


@dataclass
class PreviewProjectInput:
    job_id: str
    project_id: str


@dataclass
class ExportProjectInput:
    job_id: str
    project_id: str
    format: str = "mp4"


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


async def _stitch(
    *,
    job_id: str,
    project_id: str,
    reencode: bool,
    output_key_prefix: str,
    bucket: str,
    output_local_name: str,
) -> str:
    """Shared body for preview + export — only the codec mode + destination differ.

    All filesystem path work happens in activities; this workflow only
    composes them with deterministic strings (sandbox safe).
    """
    info = workflow.info()
    await workflow.execute_activity(
        update_job_activity,
        UpdateJobInput(
            job_id=job_id,
            status="running",
            progress=0,
            started_at=workflow.now(),
            workflow_id=info.workflow_id,
            run_id=info.run_id,
        ),
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=_DB_RETRY,
    )

    try:
        # 1. Build the ordered clip list.
        resolved: ResolveProjectClipsOutput = await workflow.execute_activity(
            resolve_project_clips_activity,
            ResolveProjectClipsInput(project_id=project_id),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )
        clip_paths = [c.local_path for c in resolved.clips]

        # 2. ffmpeg concat — activity resolves the absolute output path itself.
        concat: ConcatClipsOutput = await workflow.execute_activity(
            concat_clips_activity,
            ConcatClipsInput(
                clip_paths=clip_paths,
                output_relative_name=f"{output_key_prefix}/{output_local_name}",
                reencode=reencode,
            ),
            # Export reencode can be long for big projects; budget generously.
            start_to_close_timeout=timedelta(minutes=30 if reencode else 5),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=_FFMPEG_RETRY,
        )

        # 3. Upload (S3 with creds, else local-FS move under media/uploads/).
        object_key = f"{output_key_prefix}/{output_local_name}"
        output_url: str = await workflow.execute_activity(
            upload_render_activity,
            UploadRenderInput(local_path=concat.output_path, key=object_key, bucket=bucket),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_UPLOAD_RETRY,
        )
    except Exception as e:
        await _mark_job_failed(job_id, e)
        raise

    # 4. Finalize the Job row.
    await workflow.execute_activity(
        update_job_activity,
        UpdateJobInput(
            job_id=job_id,
            status="done",
            progress=100,
            output_url=output_url,
            finished_at=workflow.now(),
        ),
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=_DB_RETRY,
    )
    return output_url


@workflow.defn
class PreviewProjectWorkflow:
    @workflow.run
    async def run(self, input: PreviewProjectInput) -> str:
        # Unique filename per job so multiple previews coexist (per design call).
        output_name = f"project_{input.project_id}_{input.job_id}.mp4"
        return await _stitch(
            job_id=input.job_id,
            project_id=input.project_id,
            reencode=False,
            output_key_prefix="previews",
            bucket=settings.s3_bucket_renders,
            output_local_name=output_name,
        )


@workflow.defn
class ExportProjectWorkflow:
    @workflow.run
    async def run(self, input: ExportProjectInput) -> str:
        # Exports also unique — we never overwrite a finished export.
        output_name = f"project_{input.project_id}_{input.job_id}.{input.format}"
        return await _stitch(
            job_id=input.job_id,
            project_id=input.project_id,
            reencode=True,
            output_key_prefix="exports",
            bucket=settings.s3_bucket_exports,
            output_local_name=output_name,
        )
