import base64
import binascii
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.request.local_ingest_request import (
    CreateProjectFromLocalIngestRequest,
    LocalIngestFrameRequest,
)
from app.api.v1.response.from_source_response import CreateProjectFromSourceResponse
from app.api.v1.response.project_response import ProjectDetailResponse, ProjectResponse
from app.api.v1.response.scene_response import SceneResponse
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.common.enum.execution import WorkflowKind
from app.common.enum.scene import ProjectStatus
from app.common.exceptions import EntityNotFoundError
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.scene_repository import SceneRepository
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.project_model import Project
from app.service.describer_service import DescriberService
from app.service.prompt_builder_service import PromptBuilderService
from app.service.source_fetcher_service import (
    SourceType,
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

    async def get_project_detail(
        self, project_id: str, user_id: str
    ) -> ProjectDetailResponse:
        project = await self.project_repo.get_by_id(project_id)
        if project is None or project.user_id != user_id:
            # 404 not 403 — don't leak that the row exists under a different user.
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
        user_id: str,
        title: str | None = None,
        source_url: str | None = None,
    ) -> ProjectResponse:
        project = await self.project_repo.get_by_id(project_id)
        if project is None or project.user_id != user_id:
            raise EntityNotFoundError("Project", project_id)

        if title is not None:
            project.title = title
        if source_url is not None:
            project.source_url = source_url
        project.updated_at = datetime.now(timezone.utc)
        project = await self.project_repo.update(project)
        return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: str, user_id: str) -> None:
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
        if project is None or project.user_id != user_id:
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

    async def get_final_video_ref(
        self, project_id: str, user_id: str, orientation: str = "portrait"
    ) -> str:
        """Return the raw `final_<orientation>_video_url` value.

        Modern records: `supabase://<bucket>/<path>` — the controller
        re-signs these on each call (signed URLs are time-limited so we
        never persist them).
        Legacy: an absolute path on disk — the controller streams those
        directly via FileResponse. The disambiguation happens at the
        controller boundary, not here.
        """
        from fastapi import HTTPException, status

        project = await self.project_repo.get_by_id(project_id)
        if project is None or project.user_id != user_id:
            raise EntityNotFoundError("Project", project_id)

        ref = (
            project.final_landscape_video_url
            if orientation == "landscape"
            else project.final_portrait_video_url
        )
        if not ref:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Project has no {orientation} final video yet "
                    f"(status={project.status})"
                ),
            )
        return ref

    async def create_from_source(
        self,
        source_url: str,
        title: str | None = None,
        user_id: str | None = None,
        org_id: str | None = None,
        workspace_id: str | None = None,
        *,
        orientation: object | None = None,   # Orientation enum or string
        quality: object | None = None,       # Quality enum or string
        voiceover: bool | None = None,
        voice_id: str | None = None,
        voice_gender: str | None = None,
        voice_accent: str | None = None,
        target_duration: float | None = None,
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        # 1. Project shell. User-chosen render options are stamped here
        # so the first Generate doesn't need a follow-up PATCH; everything
        # is still editable via PATCH /projects/{id} later.
        project_kwargs: dict = {
            "title": title or f"From {source_type.value}",
            "source_url": source_url,
            "user_id": user_id or settings.default_user_id,
            "org_id": org_id,
            "workspace_id": workspace_id,
        }
        if orientation is not None:
            project_kwargs["orientation"] = orientation
        if quality is not None:
            project_kwargs["quality"] = quality
        if voiceover is not None:
            project_kwargs["voiceover"] = voiceover
        if voice_id is not None:
            project_kwargs["voice_id"] = voice_id
        if voice_gender is not None:
            project_kwargs["voice_gender"] = voice_gender
        if voice_accent is not None:
            project_kwargs["voice_accent"] = voice_accent
        if target_duration is not None:
            project_kwargs["target_duration"] = target_duration
        project = Project(**project_kwargs)
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
                user_id=project.user_id,
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

    async def create_from_local_ingest(
        self,
        body: CreateProjectFromLocalIngestRequest,
        user_id: str | None = None,
        org_id: str | None = None,
        workspace_id: str | None = None,
    ) -> ProjectResponse:
        """Create an analyzed Project from browser-side source capture.

        This is the primary YouTube path for production: the browser extension
        captures transcript + sampled frames while the user is already playing
        the video, and the backend only performs description/prompt synthesis.
        """
        source_url = str(body.source_url)
        try:
            source_type = classify_source_url(source_url)
        except UnsupportedSourceError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        if source_type not in (SourceType.YOUTUBE_LONG, SourceType.YOUTUBE_SHORT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Local ingest is currently supported for YouTube sources only.",
            )

        owner = user_id or settings.default_user_id
        project_kwargs: dict = {
            "title": body.title or "From local YouTube ingest",
            "source_url": source_url,
            "user_id": owner,
            "org_id": org_id,
            "workspace_id": workspace_id,
            "status": ProjectStatus.ANALYZING,
        }
        if body.orientation is not None:
            project_kwargs["orientation"] = body.orientation
        if body.quality is not None:
            project_kwargs["quality"] = body.quality
        if body.voiceover is not None:
            project_kwargs["voiceover"] = body.voiceover
        if body.voice_id is not None:
            project_kwargs["voice_id"] = body.voice_id
        if body.voice_gender is not None:
            project_kwargs["voice_gender"] = body.voice_gender
        if body.voice_accent is not None:
            project_kwargs["voice_accent"] = body.voice_accent
        if body.target_duration is not None:
            project_kwargs["target_duration"] = body.target_duration

        project = await self.project_repo.create(Project(**project_kwargs))

        storage_root = Path(settings.local_storage_path or "storage").resolve()
        frames_dir = storage_root / "projects" / project.id / "frames"
        relative_frame_paths = self._write_local_ingest_frames(
            project_id=project.id,
            frames_dir=frames_dir,
            storage_root=storage_root,
            frames=body.frames,
        )

        # Describer + prompt-builder run synchronously on the request path.
        # If either fails (LLM outage, malformed frames, timeout) the project
        # row would otherwise sit in ANALYZING forever and the FE would poll
        # a dead state. Wrap the analyze-side work so we can flip the row to
        # FAILED before re-raising, and return a proper failure status to
        # the caller instead of 201 over a half-baked project.
        duration = body.source_duration or body.target_duration or 60.0
        try:
            description = body.description
            if description is None:
                description = await DescriberService().describe(
                    relative_frame_paths,
                    body.transcript,
                    duration,
                )

            manim_prompt = PromptBuilderService().build(
                body.transcript,
                relative_frame_paths,
                description,
                duration,
            )

            project.transcript = body.transcript
            project.description = description
            project.manim_prompt = manim_prompt
            project.source_duration = duration
            project.frames_dir = str(frames_dir)
            project.status = ProjectStatus.ANALYZED
            project.updated_at = datetime.now(timezone.utc)
            await self.project_repo.update(project)
            return ProjectResponse.model_validate(project)
        except Exception as exc:
            # Best-effort: don't mask the original failure if the status
            # flip also fails.
            try:
                project.status = ProjectStatus.FAILED
                project.updated_at = datetime.now(timezone.utc)
                await self.project_repo.update(project)
            except Exception:  # noqa: BLE001
                pass
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Local ingest analyze failed: {exc}",
            ) from exc

    def _write_local_ingest_frames(
        self,
        *,
        project_id: str,
        frames_dir: Path,
        storage_root: Path,
        frames: list[LocalIngestFrameRequest],
    ) -> list[str]:
        max_frames = max(0, settings.youtube_local_ingest_max_frames)
        frames_to_write = frames[:max_frames]
        if not frames_to_write:
            return []

        frames_dir.mkdir(parents=True, exist_ok=True)
        for stale in frames_dir.glob("frame_*.jpg"):
            stale.unlink()

        relative_paths: list[str] = []
        for index, frame in enumerate(frames_to_write, 1):
            image_bytes = self._decode_local_ingest_frame(frame, index)
            frame_path = frames_dir / f"frame_{index:04d}.jpg"
            frame_path.write_bytes(image_bytes)
            relative_paths.append(str(frame_path.relative_to(storage_root)))

        return relative_paths

    def _decode_local_ingest_frame(
        self,
        frame: LocalIngestFrameRequest,
        index: int,
    ) -> bytes:
        payload = frame.image_base64
        if frame.data_url:
            header, separator, encoded = frame.data_url.partition(",")
            media_type = header.removeprefix("data:").split(";", 1)[0].lower()
            if separator != "," or "base64" not in header.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Frame {index} must be a base64 data URL.",
                )
            if media_type not in {"image/jpeg", "image/jpg"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Frame {index} must be JPEG; got {media_type or 'unknown'}.",
                )
            payload = encoded

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Frame {index} is missing image data.",
            )

        try:
            image_bytes = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Frame {index} is not valid base64.",
            ) from e

        if len(image_bytes) > settings.youtube_local_ingest_max_frame_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Frame {index} exceeds the configured frame size limit.",
            )
        if not image_bytes.startswith(b"\xff\xd8"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Frame {index} must be JPEG-encoded.",
            )
        return image_bytes

    async def generate_video(
        self,
        project_id: str,
        user_id: str,
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
        if project is None or project.user_id != user_id:
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
