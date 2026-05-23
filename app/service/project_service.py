from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from pathlib import Path

from app.api.v1.response.from_source_response import CreateProjectFromSourceResponse
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.api.v1.response.project_response import ProjectDetailResponse, ProjectResponse
from app.api.v1.response.scene_response import SceneResponse
from app.common.enum.execution import WorkflowKind
from app.common.exceptions import EntityNotFoundError
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.scene_repository import SceneRepository
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.project_model import Project
from app.service.source_fetcher_service import (
    UnsupportedSourceError,
    classify_source_url,
)
from app.service.workflow_execution_service import WorkflowExecutionService
from app.settings import settings
from app.workers.client import get_temporal_client
from app.workers.workflows.analyze_workflow import (
    AnalyzeProjectInput,
    AnalyzeProjectWorkflow,
)
from app.workers.workflows.generate_workflow import (
    GenerateVideoInput,
    GenerateVideoWorkflow,
)


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.scene_repo = SceneRepository(db)

    async def create_project(
        self,
        title: str,
        source_url: str | None = None,
        user_id: str | None = None,
        org_id: str | None = None,
        workspace_id: str | None = None,
    ) -> ProjectResponse:
        project = Project(
            title=title,
            source_url=source_url,
            user_id=user_id or settings.default_user_id,
            org_id=org_id,
            workspace_id=workspace_id,
        )
        project = await self.project_repo.create(project)
        return ProjectResponse.model_validate(project)

    async def get_project_detail(self, project_id: str) -> ProjectDetailResponse:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        scenes = await self.scene_repo.list_by_project(project_id)

        # Workflow detail (nodes/edges) returns empty for now — the new
        # workflow_service against workflow_node_instance + workflow_edge_instance
        # lands in the next refactor round.
        return ProjectDetailResponse(
            **ProjectResponse.model_validate(project).model_dump(),
            scenes=[SceneResponse.model_validate(s) for s in scenes],
            workflow=None,
        )

    async def list_projects(
        self,
        user_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        org_id: str | None = None,
        workspace_id: str | None = None,
    ) -> tuple[list[ProjectResponse], int]:
        projects, total = await self.project_repo.list_all(
            user_id, offset, limit, org_id=org_id, workspace_id=workspace_id
        )
        return [ProjectResponse.model_validate(p) for p in projects], total

    async def update_project(
        self,
        project_id: str,
        title: str | None = None,
        source_url: str | None = None,
    ) -> ProjectResponse:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        if title is not None:
            project.title = title
        if source_url is not None:
            project.source_url = source_url
        project.updated_at = datetime.now(timezone.utc)
        project = await self.project_repo.update(project)
        return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: str) -> None:
        """Delete a project end-to-end.

        Cleanup steps (best-effort; one failure must not block the rest):
          1. Find the 1:1 workflow row; soft-delete it so /workflows/{id} 404s.
          2. List every in-flight workflow_execution for the workflow and
             terminate the Temporal handle + mark the row CANCELED. Without
             this, deleting a queued project would leave a runaway Temporal
             workflow that re-writes status onto the soft-deleted project.
          3. Soft-delete the project row.
          4. rmtree the project's local storage dir (source video, frames,
             generated scripts, render artifacts). Best-effort — if files are
             held open / on a read-only mount we log and move on.

        Scene rows have no `is_deleted` column so they aren't soft-deleted
        explicitly. They become unreachable because every entry point that
        lists scenes scopes by project, and the project is now hidden.
        """
        import logging
        import shutil
        log = logging.getLogger(__name__)

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        workflow_repo = WorkflowRepository(self.db)
        workflow = await workflow_repo.get_by_project_id(project_id)
        if workflow is not None:
            execution_service = WorkflowExecutionService(self.db)
            in_flight = await execution_service.execution_repo.list_in_flight_for_workflow(
                workflow.id
            )
            if in_flight:
                await execution_service.cancel_in_flight(
                    in_flight, reason=f"Project {project_id} deleted",
                )
            workflow.is_deleted = True
            await workflow_repo.update(workflow)

        await self.project_repo.soft_delete(project)
        await self.db.commit()

        storage_root = Path(settings.local_storage_path or "storage").resolve()
        project_dir = storage_root / "projects" / project_id
        if project_dir.exists():
            try:
                shutil.rmtree(project_dir)
                log.info("delete_project: removed storage dir %s", project_dir)
            except OSError as e:
                log.warning(
                    "delete_project: failed to rmtree %s (%s) — DB delete still applied",
                    project_dir, e,
                )

    async def get_final_video_path(
        self, project_id: str, orientation: str = "portrait"
    ) -> Path:
        """Return the on-disk path of the stitched final MP4 for streaming.

        `orientation` selects which final URL to use — `final_portrait_video_url`
        or `final_landscape_video_url`. 404 if the requested orientation hasn't
        been generated.
        """
        from fastapi import HTTPException, status

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        url = (
            project.final_landscape_video_url
            if orientation == "landscape"
            else project.final_portrait_video_url
        )
        if not url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Project has no {orientation} final video yet "
                    f"(status={project.status})"
                ),
            )
        path = Path(url)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"final video url points at missing file: {path}",
            )
        return path

    async def create_from_source(
        self,
        source_url: str,
        title: str | None = None,
        user_id: str | None = None,
        org_id: str | None = None,
        workspace_id: str | None = None,
    ) -> CreateProjectFromSourceResponse:
        """Create a Project and kick off the AnalyzeProjectWorkflow on Temporal.

        Returns immediately with the (empty) Project + a Job to poll. The
        workflow runs analyze (download → frames → transcript → describer →
        prompt_builder) and writes the brief back onto the Project row.
        Frontend polls `/jobs/{id}` until `status=done`, then re-fetches the
        project to see the brief and can edit before calling /generate.
        """
        from fastapi import HTTPException, status

        try:
            source_type = classify_source_url(source_url)
        except UnsupportedSourceError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # 1. Project shell
        project = Project(
            title=title or f"From {source_type.value}",
            source_url=source_url,
            user_id=user_id or settings.default_user_id,
            org_id=org_id,
            workspace_id=workspace_id,
        )
        project = await self.project_repo.create(project)
        project_resp = ProjectResponse.model_validate(project)

        # 2. WorkflowExecution row (carries Temporal handle once started).
        execution_service = WorkflowExecutionService(self.db)
        # Reserve the temporal_workflow_id up front so the row + Temporal agree.
        execution = await execution_service.create_execution(
            project_id=project.id,
            kind=WorkflowKind.ANALYZE,
            temporal_workflow_id="",  # filled in below before start_workflow
            temporal_workflow_type=AnalyzeProjectWorkflow.__name__,
        )
        temporal_workflow_id = f"{settings.temporal_workflow_id_prefix}-analyze-{execution.id}"
        execution.temporal_workflow_id = temporal_workflow_id
        await execution_service.execution_repo.update(execution)
        await self.db.commit()

        # 3. Start AnalyzeProjectWorkflow on Temporal.
        client = await get_temporal_client()
        handle = await client.start_workflow(
            AnalyzeProjectWorkflow.run,
            AnalyzeProjectInput(
                execution_id=execution.id,
                workflow_id=execution.workflow_id,
                project_id=project.id,
                source_url=source_url,
                title_was_unset=(title is None),
            ),
            id=temporal_workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        # 4. Stamp run_id + flip status → RUNNING.
        await execution_service.stamp_handle(
            execution.id,
            temporal_run_id=handle.first_execution_run_id,
        )

        execution_resp = await execution_service.get_response(execution.id)
        return CreateProjectFromSourceResponse(
            project=project_resp,
            source_type=source_type.value,
            scenes=[],
            execution=execution_resp,
        )

    async def generate_video(
        self,
        project_id: str,
        max_clips: int = 8,
        orientations: list[str] | None = None,
    ) -> list[WorkflowExecutionResponse]:
        """Kick off one GenerateVideoWorkflow per requested orientation.

        Default `orientations` = both portrait + landscape — produces
        `final_portrait_video_url` and `final_landscape_video_url` on the
        Project row, each backed by its own per-orientation scene set
        (scene rows are scoped by (project_id, orientation, n)).

        Requires the project to already have transcript + description +
        manim_prompt populated (i.e. AnalyzeProjectWorkflow has run).
        Returns one WorkflowExecutionResponse per orientation; the FE polls
        each by its execution.id.
        """
        from fastapi import HTTPException, status

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)
        if not project.manim_prompt:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Project has no manim_prompt — run /projects/from-source first "
                    f"(current status: {project.status})"
                ),
            )

        # Default to both orientations; normalise + dedupe + validate.
        requested = orientations or ["portrait", "landscape"]
        seen: list[str] = []
        for o in requested:
            o_norm = o.lower().strip()
            if o_norm not in ("portrait", "landscape"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown orientation {o!r} — must be 'portrait' or 'landscape'",
                )
            if o_norm not in seen:
                seen.append(o_norm)

        # Source frames the per-clip generate uses for vision context (same for both).
        storage_root = Path(settings.local_storage_path or "storage").resolve()
        source_frame_paths: list[str] = []
        if project.frames_dir:
            frames_dir = Path(project.frames_dir)
            if frames_dir.exists():
                source_frame_paths = [
                    str(p.relative_to(storage_root))
                    for p in sorted(frames_dir.glob("frame_*.jpg"))
                ]

        execution_service = WorkflowExecutionService(self.db)
        client = await get_temporal_client()
        responses: list[WorkflowExecutionResponse] = []

        for orientation in seen:
            execution = await execution_service.create_execution(
                project_id=project.id,
                kind=WorkflowKind.GENERATE,
                temporal_workflow_id="",
                temporal_workflow_type=GenerateVideoWorkflow.__name__,
            )
            temporal_workflow_id = (
                f"{settings.temporal_workflow_id_prefix}-generate-{orientation}-{execution.id}"
            )
            execution.temporal_workflow_id = temporal_workflow_id
            await execution_service.execution_repo.update(execution)
            await self.db.commit()

            handle = await client.start_workflow(
                GenerateVideoWorkflow.run,
                GenerateVideoInput(
                    execution_id=execution.id,
                    project_id=project.id,
                    transcript=project.transcript or "",
                    description=project.description or "",
                    manim_prompt=project.manim_prompt,
                    source_duration=project.source_duration or 60.0,
                    orientation=orientation,
                    voiceover=bool(project.voiceover),
                    voice_id=project.voice_id or "",
                    quality="ql",
                    max_clips=max_clips,
                    source_frame_paths=source_frame_paths,
                ),
                id=temporal_workflow_id,
                task_queue=settings.temporal_task_queue,
            )

            await execution_service.stamp_handle(
                execution.id,
                temporal_run_id=handle.first_execution_run_id,
            )
            responses.append(await execution_service.get_response(execution.id))

        return responses
