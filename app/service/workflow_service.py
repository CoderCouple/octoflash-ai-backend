from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.workflow_response import (
    WorkflowEdgeResponse,
    WorkflowNodeResponse,
    WorkflowResponse,
)
from app.common.enum.workflow import EdgeKind, NodeKind
from app.common.exceptions import EntityNotFoundError
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.workflow_edge_model import WorkflowEdge
from app.model.workflow_node_model import WorkflowNode


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.workflow_repo = WorkflowRepository(db)

    async def get_workflow(self, project_id: str) -> WorkflowResponse:
        nodes = await self.workflow_repo.list_nodes(project_id)
        edges = await self.workflow_repo.list_edges(project_id)
        return WorkflowResponse(
            nodes=[WorkflowNodeResponse.model_validate(n) for n in nodes],
            edges=[WorkflowEdgeResponse.model_validate(e) for e in edges],
        )

    async def add_branch(
        self,
        project_id: str,
        from_node_id: str,
        branch_label: str,
        style_override: str | None = None,
    ) -> WorkflowResponse:
        """Add a branch node downstream of `from_node_id`.

        Creates a new BRANCH node + an edge from `from_node_id` to it. The
        scenes on the branch get rendered with `style_override` applied (e.g.
        the Manic preset), implementing the "multiple cuts from same scenes"
        feature in the brief.
        """
        # Validate `from_node_id` exists in this project
        existing_nodes = await self.workflow_repo.list_nodes(project_id)
        if not any(n.id == from_node_id for n in existing_nodes):
            raise EntityNotFoundError("WorkflowNode", from_node_id)

        branch_node = WorkflowNode(
            project_id=project_id,
            kind=NodeKind.BRANCH.value,
            x=0,
            y=0,
            label=branch_label,
            branch_label=branch_label,
            style_override=style_override,
        )
        branch_node = await self.workflow_repo.create_node(branch_node)

        edge = WorkflowEdge(
            project_id=project_id,
            from_node_id=from_node_id,
            to_node_id=branch_node.id,
            kind=EdgeKind.BRANCH.value,
        )
        await self.workflow_repo.create_edge(edge)

        return await self.get_workflow(project_id)
