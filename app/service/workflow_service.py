"""WorkflowService — load / save the canonical React Flow DAG.

Save flow (PUT /workflows/:id):
  1. Validate every node references a known workflow_node_type (machine key).
  2. Validate every edge's source/target appears in the node list.
  3. Persist `workflow.definition` JSONB verbatim.
  4. Replace projection rows in workflow_node_instance + workflow_edge_instance.

Load flow (GET /workflows/:id):
  Return Workflow + hydrated projection rows. `definition` is what the React
  Flow editor passes back to `<ReactFlow {...defn} />`.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.request.workflow_request import PutWorkflowRequest, WorkflowNodeIn
from app.api.v1.response.workflow_response import (
    WorkflowEdgeInstanceResponse,
    WorkflowNodeInstanceResponse,
    WorkflowResponse,
)
from app.common.exceptions import EntityNotFoundError
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.workflow_edge_instance_model import WorkflowEdgeInstance
from app.model.workflow_model import Workflow
from app.model.workflow_node_instance_model import WorkflowNodeInstance


# Keys in node.data that map to typed columns; everything else goes into
# workflow_node_instance.config JSONB.
_RESERVED_DATA_KEYS = {"scene_id", "label"}


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.workflow_repo = WorkflowRepository(db)
        self.project_repo = ProjectRepository(db)

    # ── load ────────────────────────────────────────────────────────────

    async def get_for_project(self, project_id: str) -> WorkflowResponse:
        """Sugar: return the Project's 1:1 workflow, creating an empty one if missing."""
        workflow = await self.workflow_repo.get_by_project_id(project_id)
        if workflow is None:
            project = await self.project_repo.get_by_id(project_id)
            if project is None:
                raise EntityNotFoundError("Project", project_id)
            workflow = Workflow(
                project_id=project_id,
                user_id=project.user_id,
                name=project.title,
            )
            workflow = await self.workflow_repo.create(workflow)
            await self.db.commit()
        return await self._to_response(workflow)

    async def get_by_id(self, workflow_id: str) -> WorkflowResponse:
        workflow = await self.workflow_repo.get_by_id(workflow_id)
        if workflow is None:
            raise EntityNotFoundError("Workflow", workflow_id)
        return await self._to_response(workflow)

    # ── save ────────────────────────────────────────────────────────────

    async def put_definition(
        self, workflow_id: str, payload: PutWorkflowRequest
    ) -> WorkflowResponse:
        workflow = await self.workflow_repo.get_by_id(workflow_id)
        if workflow is None:
            raise EntityNotFoundError("Workflow", workflow_id)

        defn = payload.definition
        node_ids = {n.id for n in defn.nodes}

        # Validate every edge endpoint exists in the node list.
        bad_edges = [
            e for e in defn.edges
            if e.source not in node_ids or e.target not in node_ids
        ]
        if bad_edges:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{len(bad_edges)} edges reference unknown nodes "
                       f"(first: {bad_edges[0].id} → source={bad_edges[0].source!r}, "
                       f"target={bad_edges[0].target!r})",
            )

        # Resolve every node's semantic type → workflow_node_type.id.
        # React Flow sets `node.type` to the *renderer* component name (e.g.
        # "OctoflashNode" — the FE registers one renderer for all node kinds)
        # and stores the semantic kind in `node.data.type`. Prefer the latter;
        # fall back to top-level `type` for older payloads that wrote it there.
        node_rows: list[WorkflowNodeInstance] = []
        for n in defn.nodes:
            semantic_type = n.data.get("type") or n.type
            type_row = await self.workflow_repo.get_node_type_by_key(semantic_type)
            if type_row is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown node type {semantic_type!r} (node id {n.id})",
                )
            node_rows.append(_node_to_instance(n, workflow_id, type_row.id))

        edge_rows = [
            WorkflowEdgeInstance(
                id=e.id,
                workflow_id=workflow_id,
                source_instance_id=e.source,
                target_instance_id=e.target,
                source_handle=e.sourceHandle,
                target_handle=e.targetHandle,
                label=e.label,
                data=e.data,
            )
            for e in defn.edges
        ]

        # Persist definition JSONB + sync projections.
        workflow.definition = payload.definition.model_dump()
        if payload.name is not None:
            workflow.name = payload.name
        if payload.description is not None:
            workflow.description = payload.description
        await self.workflow_repo.update(workflow)
        await self.workflow_repo.replace_projections(workflow_id, node_rows, edge_rows)

        return await self._to_response(workflow)

    # ── helpers ─────────────────────────────────────────────────────────

    async def _to_response(self, workflow: Workflow) -> WorkflowResponse:
        nodes = await self.workflow_repo.list_node_instances(workflow.id)
        edges = await self.workflow_repo.list_edge_instances(workflow.id)
        return WorkflowResponse(
            id=workflow.id,
            project_id=workflow.project_id,
            user_id=workflow.user_id,
            name=workflow.name,
            description=workflow.description,
            definition=workflow.definition,
            execution_plan=workflow.execution_plan,
            status=workflow.status,
            cron=workflow.cron,
            last_run_at=workflow.last_run_at,
            last_run_id=workflow.last_run_id,
            last_run_status=workflow.last_run_status,
            next_run_at=workflow.next_run_at,
            nodes=[WorkflowNodeInstanceResponse.model_validate(n) for n in nodes],
            edges=[WorkflowEdgeInstanceResponse.model_validate(e) for e in edges],
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )


def _node_to_instance(
    node: WorkflowNodeIn, workflow_id: str, type_id: str
) -> WorkflowNodeInstance:
    """Project a React Flow node into a workflow_node_instance row.

    `data.scene_id` (if present) becomes the FK; `data.label` overrides the
    top-level label; anything else in `data` lands in `config` JSONB.
    """
    extra_config = {k: v for k, v in node.data.items() if k not in _RESERVED_DATA_KEYS}
    return WorkflowNodeInstance(
        id=node.id,
        workflow_id=workflow_id,
        type_id=type_id,
        scene_id=node.data.get("scene_id"),
        x=node.position.x,
        y=node.position.y,
        w=node.width,
        h=node.height,
        label=node.data.get("label") or node.label,
        config=extra_config or None,
    )
