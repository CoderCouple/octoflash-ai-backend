"""PublishService — orchestrates POST /targets/{id}/publish.

Two stages:

  1. **Pre-flight (sync, in the request thread)** — load Target + Project +
     Credential, resolve the local video path for the requested orientation,
     refresh the token if needed, write a workflow_execution row.

  2. **Long-run (Temporal)** — `PublishTargetWorkflow` runs the actual
     `publish_target_activity` against the platform. Heartbeats are owned by
     the activity since the upload can take minutes.

The endpoint returns 202 + the execution; the FE polls /executions/{id}.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.common.enum.execution import WorkflowKind
from app.common.exceptions import EntityNotFoundError
from app.db.repository.credential_repository import CredentialRepository
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.target_repository import TargetRepository
from app.service.oauth_refresh import load_fresh_token
from app.service.oauth_service import OAuthError
from app.service.publish.registry import PUBLISHERS
from app.service.publish.models import PublishMetadata
from app.service.workflow_execution_service import WorkflowExecutionService
from app.settings import settings
from app.workers.client import get_temporal_client
from app.workers.workflows.publish_workflow import (
    PublishTargetInput,
    PublishTargetWorkflow,
)

log = logging.getLogger(__name__)


class PublishService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.target_repo = TargetRepository(db)
        self.project_repo = ProjectRepository(db)
        self.credential_repo = CredentialRepository(db)

    async def publish(
        self,
        *,
        target_id: str,
        project_id: str,
        orientation: str,
        metadata: PublishMetadata,
        user_id: str,
    ) -> WorkflowExecutionResponse:
        target = await self.target_repo.get_by_id(target_id)
        if target is None or target.user_id != user_id:
            # 404 not 403 — don't leak that the row exists under a different user.
            raise EntityNotFoundError("Target", target_id)
        if target.credential_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Target {target_id} has no credential — reconnect via "
                    f"GET /api/v1/targets/oauth/{target.platform.value}/authorize."
                ),
            )

        # Reject early if the platform isn't wired (TikTok/IG/LinkedIn/X
        # today). The dispatcher would raise PublishError otherwise; this
        # short-circuit gives a clean 501 before we burn an execution row.
        platform = target.platform
        publisher = PUBLISHERS.get(platform)
        if publisher is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Publish for platform {platform.value!r} not registered.",
            )
        from app.service.publish._stubs import _not_implemented as _stub_marker
        # _stubs publishers eventually call _not_implemented. Detect them by
        # checking the function's __wrapped__ module — cheap and explicit.
        if publisher.__module__.endswith("publish._stubs"):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    f"{platform.value} publish path is a stub. Wire it up in "
                    "app/service/publish/ before retrying."
                ),
            )

        project = await self.project_repo.get_by_id(project_id)
        if project is None or project.user_id != user_id:
            raise EntityNotFoundError("Project", project_id)

        video_path = self._video_path(project, orientation)
        if not video_path or not video_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Project {project_id} has no {orientation} final video to publish. "
                    f"Run Generate first."
                ),
            )

        # Refresh token in the request thread so the activity below uses a
        # known-good token and we don't pay refresh latency inside the
        # Temporal activity's wall clock.
        credential = await self.credential_repo.get_by_id(target.credential_id)
        if credential is None:
            raise EntityNotFoundError("Credential", target.credential_id)
        try:
            token = await load_fresh_token(
                credential=credential,
                platform=platform,
                credential_repo=self.credential_repo,
            )
        except OAuthError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{platform.value} token unusable: {e}. Reconnect the target.",
            )

        # Execution row + Temporal kickoff (mirrors ProjectService.create_from_source).
        execution_service = WorkflowExecutionService(self.db)
        execution = await execution_service.create_execution(
            project_id=project.id,
            kind=WorkflowKind.EXPORT,        # EXPORT covers "send out the final"
            temporal_workflow_id="",
            temporal_workflow_type=PublishTargetWorkflow.__name__,
        )
        temporal_workflow_id = (
            f"{settings.temporal_workflow_id_prefix}-publish-{execution.id}"
        )
        execution.temporal_workflow_id = temporal_workflow_id
        await execution_service.execution_repo.update(execution)
        await self.db.commit()

        client = await get_temporal_client()
        handle = await client.start_workflow(
            PublishTargetWorkflow.run,
            PublishTargetInput(
                execution_id=execution.id,
                target_id=target.id,
                project_id=project.id,
                orientation=orientation,
                video_path=str(video_path),
                platform=platform.value,
                access_token=token.access_token,
                title=metadata.title,
                description=metadata.description,
                tags=list(metadata.tags),
                privacy=metadata.privacy,
                extra={str(k): str(v) for k, v in metadata.extra.items()},
            ),
            id=temporal_workflow_id,
            task_queue=settings.temporal_task_queue,
        )
        await execution_service.stamp_handle(
            execution_id=execution.id,
            temporal_run_id=handle.first_execution_run_id,
        )
        await self.db.refresh(execution)
        return await execution_service.get_response(execution.id)

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _video_path(project, orientation: str) -> Path | None:
        """Resolve project.final_*_video_url for the requested orientation
        into an absolute Path under settings.local_storage_path."""
        url = (
            project.final_portrait_video_url
            if orientation == "portrait"
            else project.final_landscape_video_url
        )
        if not url:
            return None
        p = Path(url)
        if p.is_absolute():
            return p
        return (Path(settings.local_storage_path or "storage").resolve() / p).resolve()
