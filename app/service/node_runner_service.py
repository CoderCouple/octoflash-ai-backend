"""NodeRunnerService — start a Temporal workflow for one DAG node.

The "Run" / "Regenerate" buttons in the FE call `POST /workflows/{wf_id}/
nodes/{wni_id}/run`, which routes here. Each semantic node-kind maps to a
Temporal workflow via the `_NODE_KIND_RUNNERS` registry below.

Coalescing: the temporal_workflow_id is deterministic per (node_id, config
hash). Temporal's `WorkflowIDReusePolicy.REJECT_DUPLICATE` makes a second
click with identical config return the in-flight execution's id instead of
starting a new one. Different config → different hash → new run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.common import WorkflowIDReusePolicy

from app.common.enum.execution import WorkflowKind
from app.common.exceptions import EntityNotFoundError
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.scene_repository import SceneRepository
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.scene_model import Scene
from app.model.workflow_node_instance_model import WorkflowNodeInstance
from app.service.workflow_execution_service import WorkflowExecutionService
from app.settings import settings
from app.workers.client import get_temporal_client
from app.workers.workflows.analyze_workflow import AnalyzeProjectInput, AnalyzeProjectWorkflow
from app.workers.workflows.regenerate_workflow import (
    RegenerateClipInput,
    RegenerateClipWorkflow,
)


@dataclass
class _Dispatched:
    """Result of mapping a node kind to a Temporal workflow start."""
    workflow_cls: type
    workflow_run: Any
    workflow_input: Any
    kind: WorkflowKind
    handle_prefix: str           # e.g. "analyze", "regen" — shows up in temporal_workflow_id
    config_for_hash: dict[str, Any]   # what to hash for the dedupe id


class NodeRunnerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.workflow_repo = WorkflowRepository(db)
        self.project_repo = ProjectRepository(db)
        self.scene_repo = SceneRepository(db)

    async def run_node(
        self,
        *,
        workflow_id: str,
        node_instance_id: str,
        inputs_override: dict[str, Any] | None = None,
    ):
        """Kick off the Temporal workflow associated with this node's kind.

        Returns the WorkflowExecutionResponse (same envelope the project-level
        routes return, so the FE polls /executions/:id the same way).
        """
        # Lazy import — avoids circular ref via WorkflowExecutionService → response.
        from app.api.v1.response.workflow_execution_response import (
            WorkflowExecutionResponse,
        )

        # 1. Load node + workflow + node-type
        node = await self.workflow_repo.get_node_instance_by_id(node_instance_id)
        if node is None or node.workflow_id != workflow_id:
            raise EntityNotFoundError("WorkflowNodeInstance", node_instance_id)
        workflow = await self.workflow_repo.get_by_id(workflow_id)
        if workflow is None:
            raise EntityNotFoundError("Workflow", workflow_id)
        # type_id is FK to workflow_node_type — fetch the row to get the key
        node_type = next(
            (t for t in await self.workflow_repo.list_node_types() if t.id == node.type_id),
            None,
        )
        if node_type is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Node {node_instance_id} has dangling type_id {node.type_id!r}",
            )

        project = await self.project_repo.get_by_id(workflow.project_id)
        if project is None:
            raise EntityNotFoundError("Project", workflow.project_id)

        # 2. Build the runner inputs from node.config + the override.
        merged_config: dict[str, Any] = dict(node.config or {})
        if inputs_override:
            merged_config.update(inputs_override)

        # 3. Dispatch.
        dispatched = await self._dispatch(
            node_kind=node_type.type,
            node=node,
            project=project,
            merged_config=merged_config,
        )

        # 4. Deterministic temporal_workflow_id → coalesces duplicate clicks.
        config_hash = hashlib.sha256(
            json.dumps(dispatched.config_for_hash, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]
        temporal_workflow_id = (
            f"{settings.temporal_workflow_id_prefix}-{dispatched.handle_prefix}-"
            f"{node.id}-{config_hash}"
        )

        # 5. Create the execution row.
        execution_service = WorkflowExecutionService(self.db)
        execution = await execution_service.create_execution(
            project_id=project.id,
            kind=dispatched.kind,
            temporal_workflow_id=temporal_workflow_id,
            temporal_workflow_type=dispatched.workflow_cls.__name__,
            node_instance_id=node.id,
        )
        await self.db.commit()

        # 6. Refresh dispatched input with the real execution_id (the workflow
        #    needs it to write progress back).
        if hasattr(dispatched.workflow_input, "execution_id"):
            dispatched.workflow_input.execution_id = execution.id

        # 7. Kick off Temporal — REJECT_DUPLICATE coalesces same-config reclicks.
        client = await get_temporal_client()
        handle = await client.start_workflow(
            dispatched.workflow_run,
            dispatched.workflow_input,
            id=temporal_workflow_id,
            task_queue=settings.temporal_task_queue,
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        )

        # 8. Flip to RUNNING + stamp the Temporal run_id.
        await execution_service.stamp_handle(
            execution_id=execution.id,
            temporal_run_id=handle.first_execution_run_id,
        )
        await self.db.refresh(execution)
        return WorkflowExecutionResponse.model_validate(execution)

    # ── per-kind dispatchers ─────────────────────────────────────────────

    async def _dispatch(
        self,
        *,
        node_kind: str,
        node: WorkflowNodeInstance,
        project,
        merged_config: dict[str, Any],
    ) -> _Dispatched:
        runner = _NODE_KIND_RUNNERS.get(node_kind)
        if runner is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Running node kind {node_kind!r} is not implemented yet.",
            )
        return await runner(self, node=node, project=project, merged_config=merged_config)

    async def _run_analyze_like(
        self, *, node: WorkflowNodeInstance, project, merged_config: dict[str, Any],
    ) -> _Dispatched:
        """source_url + analyze: re-run AnalyzeProjectWorkflow for this project."""
        source_url = merged_config.get("source_url") or project.source_url
        if not source_url:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project has no source_url to analyze.",
            )
        return _Dispatched(
            workflow_cls=AnalyzeProjectWorkflow,
            workflow_run=AnalyzeProjectWorkflow.run,
            workflow_input=AnalyzeProjectInput(
                execution_id="",  # filled in after create_execution
                workflow_id=node.workflow_id,
                project_id=project.id,
                source_url=source_url,
                title_was_unset=False,  # title already set on rerun
            ),
            kind=WorkflowKind.ANALYZE,
            handle_prefix="analyze",
            config_for_hash={"source_url": source_url},
        )

    async def _run_scene(
        self, *, node: WorkflowNodeInstance, project, merged_config: dict[str, Any],
    ) -> _Dispatched:
        """scene: regenerate the clip backed by this node.

        Phase 1: the seeded DAG places placeholder scene nodes with no
        scene_id. Real scenes only exist after the user clicks Generate (the
        existing GenerateVideoWorkflow materializes scene rows). So we 409
        when there's no scene_id yet.
        """
        if not node.scene_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This scene node hasn't been rendered yet. Click Generate "
                    "on the project first; then per-scene regenerate is available."
                ),
            )
        scene = await self.scene_repo.get_by_id(node.scene_id)
        if scene is None:
            raise EntityNotFoundError("Scene", node.scene_id)
        if not project.manim_prompt:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project has no manim_prompt — run analyze first.",
            )

        # Collect sibling ordered paths (same shape SceneService.regenerate_clip uses).
        siblings = await self.scene_repo.list_by_project(project.id)
        ordered_paths = [str(s.video_url) for s in sorted(siblings, key=lambda s: s.n)]

        storage_root = Path(settings.local_storage_path or "storage").resolve()
        source_frame_paths: list[str] = []
        if project.frames_dir:
            frames_dir = Path(project.frames_dir)
            if frames_dir.exists():
                source_frame_paths = [
                    str(p.relative_to(storage_root))
                    for p in sorted(frames_dir.glob("frame_*.jpg"))
                ]

        # Allow the FE to override prompt/duration via inputs.
        prompt = merged_config.get("brief") or scene.prompt or ""
        duration = float(merged_config.get("duration") or scene.duration or 8.0)
        title = merged_config.get("title") or scene.title or f"Clip {scene.n}"
        orientation = (
            project.orientation.value if hasattr(project.orientation, "value")
            else (project.orientation or "portrait")
        )

        return _Dispatched(
            workflow_cls=RegenerateClipWorkflow,
            workflow_run=RegenerateClipWorkflow.run,
            workflow_input=RegenerateClipInput(
                execution_id="",
                project_id=project.id,
                scene_id=scene.id,
                n=scene.n,
                title=title,
                clip_prompt=prompt,
                duration=duration,
                transcript=project.transcript or "",
                description=project.description or "",
                manim_prompt=project.manim_prompt,
                orientation=orientation,
                sibling_clip_paths=ordered_paths,
                source_frame_paths=source_frame_paths,
            ),
            kind=WorkflowKind.REGENERATE_CLIP,
            handle_prefix="noderun-scene",
            config_for_hash={
                "scene_id": scene.id,
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:8],
                "duration": duration,
            },
        )


# Registry. Maps semantic node-type key → bound method on NodeRunnerService.
# Stays at the bottom because each entry references methods defined above.
_NODE_KIND_RUNNERS: dict[str, Callable[..., Awaitable[_Dispatched]]] = {
    "source_url": NodeRunnerService._run_analyze_like,
    "analyze":    NodeRunnerService._run_analyze_like,
    "scene":      NodeRunnerService._run_scene,
    # "source_text" and "target" intentionally absent — runner raises 501.
}
