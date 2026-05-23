"""PublishTargetWorkflow — durable upload of a final render to one Target.

Steps:
  1. update_execution: status=RUNNING + stamp Temporal handle
  2. publish_target_activity: actual upload (Resumable for YT, etc.)
  3. update_execution: status=COMPLETED + log_entry with the platform URL

Activity-level retries handle transient network failures; workflow-level
retries are off (no point uploading twice if attempt 1 finalized but the
status write failed — that'd publish duplicates). If the activity exhausts
its retries we mark FAILED and surface the platform error on the FE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workers.activities.db_activity import (
        UpdateExecutionInput,
        update_execution_activity,
    )
    from app.workers.activities.publish_activity import (
        PublishActivityInput,
        PublishActivityOutput,
        publish_target_activity,
    )


_DB_RETRY = RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=5)
_PUBLISH_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_attempts=3,
)


@dataclass
class PublishTargetInput:
    execution_id: str
    target_id: str
    project_id: str
    orientation: str
    platform: str
    video_path: str
    access_token: str
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    privacy: str = "private"
    extra: dict[str, str] = field(default_factory=dict)


@workflow.defn
class PublishTargetWorkflow:
    @workflow.run
    async def run(self, input: PublishTargetInput) -> dict:
        info = workflow.info()
        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=input.execution_id,
                status="RUNNING",
                started_at=workflow.now(),
                temporal_workflow_id=info.workflow_id,
                temporal_run_id=info.run_id,
                log_entry={
                    "step": "publishing",
                    "platform": input.platform,
                    "orientation": input.orientation,
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        try:
            result: PublishActivityOutput = await workflow.execute_activity(
                publish_target_activity,
                PublishActivityInput(
                    target_id=input.target_id,
                    project_id=input.project_id,
                    orientation=input.orientation,
                    platform=input.platform,
                    video_path=input.video_path,
                    access_token=input.access_token,
                    title=input.title,
                    description=input.description,
                    tags=list(input.tags),
                    privacy=input.privacy,
                    extra=dict(input.extra),
                ),
                # Large clips take minutes; give plenty of room.
                start_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=_PUBLISH_RETRY,
            )
        except Exception as e:
            await workflow.execute_activity(
                update_execution_activity,
                UpdateExecutionInput(
                    execution_id=input.execution_id,
                    status="FAILED",
                    completed_at=workflow.now(),
                    log_entry={
                        "step": "publish_failed",
                        "error_type": type(e).__name__,
                        "error_message": str(e)[:500],
                    },
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DB_RETRY,
            )
            raise

        await workflow.execute_activity(
            update_execution_activity,
            UpdateExecutionInput(
                execution_id=input.execution_id,
                status="COMPLETED",
                completed_at=workflow.now(),
                log_entry={
                    "step": "published",
                    "platform_video_id": result.platform_video_id,
                    "platform_url": result.platform_url,
                },
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
        )

        return {
            "platform_video_id": result.platform_video_id,
            "platform_url": result.platform_url,
        }
