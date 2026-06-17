from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.api.v1.response.scene_response import SceneResponse
from app.common.enum.execution import WorkflowKind
from app.common.exceptions import EntityNotFoundError
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.scene_repository import SceneRepository
from app.model.scene_model import Scene
from app.service.workflow_execution_service import WorkflowExecutionService
from app.settings import settings
from app.workers.client import get_temporal_client
from app.workers.workflows.regenerate_workflow import (
    RegenerateClipInput,
    RegenerateClipWorkflow,
)


class SceneService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scene_repo = SceneRepository(db)
        self.project_repo = ProjectRepository(db)

    async def add_scene(
        self,
        project_id: str,
        user_id: str,
        title: str | None = None,
        prompt: str | None = None,
        duration: float | None = None,
        n: int | None = None,
    ) -> SceneResponse:
        # Ownership: scenes are scoped via the parent project's user_id.
        project = await self.project_repo.get_by_id(project_id)
        if project is None or project.user_id != user_id:
            raise EntityNotFoundError("Project", project_id)
        slot = n if n is not None else await self.scene_repo.next_n_for_project(project_id)
        scene = Scene(
            project_id=project_id,
            n=slot,
            title=title,
            prompt=prompt,
            duration=duration,
        )
        scene = await self.scene_repo.create(scene)
        return SceneResponse.model_validate(scene)

    async def get_scene(self, scene_id: str, user_id: str) -> SceneResponse:
        scene = await self.scene_repo.get_by_id(scene_id)
        if scene is None:
            raise EntityNotFoundError("Scene", scene_id)
        project = await self.project_repo.get_by_id(scene.project_id)
        if project is None or project.user_id != user_id:
            # 404 not 403 — don't leak that the row exists under a different user.
            raise EntityNotFoundError("Scene", scene_id)
        return SceneResponse.model_validate(scene)

    async def get_scene_preview_path(self, scene_id: str, user_id: str) -> Path:
        """Return the on-disk MP4 path for streaming. Raises if missing."""
        from fastapi import HTTPException, status

        scene = await self.scene_repo.get_by_id(scene_id)
        if scene is None:
            raise EntityNotFoundError("Scene", scene_id)
        project = await self.project_repo.get_by_id(scene.project_id)
        if project is None or project.user_id != user_id:
            raise EntityNotFoundError("Scene", scene_id)
        if not scene.video_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene {scene_id} has no rendered video yet (status={scene.status})",
            )
        path = Path(scene.video_url)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Scene video_url points at missing file: {path}",
            )
        return path

    async def update_scene(
        self,
        scene_id: str,
        user_id: str,
        title: str | None = None,
        prompt: str | None = None,
        duration: float | None = None,
    ) -> SceneResponse:
        scene = await self.scene_repo.get_by_id(scene_id)
        if scene is None:
            raise EntityNotFoundError("Scene", scene_id)
        project = await self.project_repo.get_by_id(scene.project_id)
        if project is None or project.user_id != user_id:
            raise EntityNotFoundError("Scene", scene_id)

        if title is not None:
            scene.title = title
        if prompt is not None:
            scene.prompt = prompt
        if duration is not None:
            scene.duration = duration
        scene.updated_at = datetime.now(timezone.utc)
        scene = await self.scene_repo.update(scene)
        return SceneResponse.model_validate(scene)

    async def delete_scene(self, scene_id: str, user_id: str) -> None:
        """Delete one scene + clean up everything that points at it.

        Cleanup:
          1. Find the project's workflow, then any in-flight workflow_execution
             whose triggering DAG node was this scene → terminate Temporal +
             mark CANCELED.
          2. Hard-delete the scene. FK ON DELETE SET NULL on
             workflow_node_instance.scene_id zeroes the DAG node's link
             automatically; the placeholder node stays on the canvas so the
             user can choose to delete it or re-render.
          3. Best-effort rmtree of any per-scene files (generated script,
             intermediate renders) under storage/scripts/{scene_id}/.
        """
        import logging
        import shutil
        from app.db.repository.workflow_repository import WorkflowRepository
        log = logging.getLogger(__name__)

        scene = await self.scene_repo.get_by_id(scene_id)
        if scene is None:
            raise EntityNotFoundError("Scene", scene_id)
        project = await self.project_repo.get_by_id(scene.project_id)
        if project is None or project.user_id != user_id:
            raise EntityNotFoundError("Scene", scene_id)

        workflow_repo = WorkflowRepository(self.db)
        workflow = await workflow_repo.get_by_project_id(scene.project_id)
        if workflow is not None:
            execution_service = WorkflowExecutionService(self.db)
            in_flight = await execution_service.execution_repo.list_in_flight_for_scene(
                scene_id=scene_id, workflow_id=workflow.id,
            )
            if in_flight:
                await execution_service.cancel_in_flight(
                    in_flight, reason=f"Scene {scene_id} deleted",
                )

        await self.scene_repo.delete(scene)
        await self.db.commit()

        # Best-effort filesystem cleanup. Scene scripts live under
        # ./storage/scripts/{scene_id}/ per script_generator_service.
        storage_root = Path(settings.local_storage_path or "storage").resolve()
        scripts_dir = storage_root / "scripts" / scene_id
        if scripts_dir.exists():
            try:
                shutil.rmtree(scripts_dir)
                log.info("delete_scene: removed %s", scripts_dir)
            except OSError as e:
                log.warning(
                    "delete_scene: failed to rmtree %s (%s) — DB delete still applied",
                    scripts_dir, e,
                )

    async def regenerate_clip(
        self, scene_id: str, user_id: str
    ) -> WorkflowExecutionResponse:
        """Kick off RegenerateClipWorkflow — re-renders just this clip + re-stitches the project.

        Reads the latest Scene + Project state, denormalizes both into the workflow
        input (so activities don't re-read), and returns a Job to poll.
        """
        from fastapi import HTTPException, status

        scene = await self.scene_repo.get_by_id(scene_id)
        if scene is None:
            raise EntityNotFoundError("Scene", scene_id)
        project = await self.project_repo.get_by_id(scene.project_id)
        if project is None or project.user_id != user_id:
            # 404 not 403 — don't leak that the row exists under a different user.
            raise EntityNotFoundError("Scene", scene_id)
        if not project.manim_prompt:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Project has no manim_prompt — run analyze first "
                    f"(current status: {project.status})"
                ),
            )

        # Collect ordered video paths for all sibling clips (we'll splice this
        # clip's new render into position before concat).
        siblings = await self.scene_repo.list_by_project(project.id)
        ordered_paths = [str(s.video_url) for s in sorted(siblings, key=lambda s: s.n)]

        # Source frames (for vision context inside per-clip script_gen)
        storage_root = Path(settings.local_storage_path or "storage").resolve()
        source_frame_paths: list[str] = []
        if project.frames_dir:
            frames_dir = Path(project.frames_dir)
            if frames_dir.exists():
                source_frame_paths = [
                    str(p.relative_to(storage_root))
                    for p in sorted(frames_dir.glob("frame_*.jpg"))
                ]

        # WorkflowExecution row + Temporal kickoff.
        execution_service = WorkflowExecutionService(self.db)
        execution = await execution_service.create_execution(
            project_id=project.id,
            kind=WorkflowKind.REGENERATE_CLIP,
            temporal_workflow_id="",
            temporal_workflow_type=RegenerateClipWorkflow.__name__,
        )
        temporal_workflow_id = f"{settings.temporal_workflow_id_prefix}-regen-{execution.id}"
        execution.temporal_workflow_id = temporal_workflow_id
        await execution_service.execution_repo.update(execution)
        await self.db.commit()

        client = await get_temporal_client()
        handle = await client.start_workflow(
            RegenerateClipWorkflow.run,
            RegenerateClipInput(
                execution_id=execution.id,
                project_id=project.id,
                scene_id=scene.id,
                n=scene.n,
                title=scene.title or f"Clip {scene.n}",
                clip_prompt=scene.prompt or "",
                duration=scene.duration or 8.0,
                transcript=project.transcript or "",
                description=project.description or "",
                manim_prompt=project.manim_prompt,
                orientation=(
                    project.orientation.value if hasattr(project.orientation, "value")
                    else (project.orientation or "portrait")
                ),
                voiceover=bool(project.voiceover),
                voice_id=project.voice_id or "",
                quality="ql",
                all_clip_paths_in_order=ordered_paths,
                source_frame_paths=source_frame_paths,
            ),
            id=temporal_workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        await execution_service.stamp_handle(
            execution.id,
            temporal_run_id=handle.first_execution_run_id,
        )

        return await execution_service.get_response(execution.id)
