from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.workflow_edge_model import WorkflowEdge
from app.model.workflow_node_model import WorkflowNode


class WorkflowRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_nodes(self, project_id: str) -> list[WorkflowNode]:
        result = await self.db.execute(
            select(WorkflowNode).where(WorkflowNode.project_id == project_id)
        )
        return list(result.scalars().all())

    async def list_edges(self, project_id: str) -> list[WorkflowEdge]:
        result = await self.db.execute(
            select(WorkflowEdge).where(WorkflowEdge.project_id == project_id)
        )
        return list(result.scalars().all())

    async def create_node(self, node: WorkflowNode) -> WorkflowNode:
        self.db.add(node)
        await self.db.flush()
        return node

    async def create_edge(self, edge: WorkflowEdge) -> WorkflowEdge:
        self.db.add(edge)
        await self.db.flush()
        return edge

    async def delete_node(self, node: WorkflowNode) -> None:
        await self.db.delete(node)
        await self.db.flush()

    async def delete_edge(self, edge: WorkflowEdge) -> None:
        await self.db.delete(edge)
        await self.db.flush()
