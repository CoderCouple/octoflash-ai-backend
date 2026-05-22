"""Repository for `workflow` + its projection tables (workflow_node_instance,
workflow_edge_instance).

Save semantics: `workflow.definition` JSONB is the source of truth. The two
projection tables are mirrored on every PUT via DELETE + INSERT (small N,
not worth a diff). The edge table cascades on the node FK, so deleting the
nodes for a workflow nukes its edges first; we delete edges explicitly
anyway to keep the transaction order predictable.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.workflow_edge_instance_model import WorkflowEdgeInstance
from app.model.workflow_model import Workflow
from app.model.workflow_node_instance_model import WorkflowNodeInstance
from app.model.workflow_node_type_model import WorkflowNodeType


class WorkflowRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── workflow row ──────────────────────────────────────────────────────

    async def get_by_id(self, workflow_id: str) -> Workflow | None:
        result = await self.db.execute(
            select(Workflow).where(
                Workflow.id == workflow_id,
                Workflow.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_by_project_id(self, project_id: str) -> Workflow | None:
        result = await self.db.execute(
            select(Workflow).where(
                Workflow.project_id == project_id,
                Workflow.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def create(self, workflow: Workflow) -> Workflow:
        self.db.add(workflow)
        await self.db.flush()
        return workflow

    async def update(self, workflow: Workflow) -> Workflow:
        workflow.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return workflow

    # ── node-type library lookup ──────────────────────────────────────────

    async def get_node_type_by_key(self, type_key: str) -> WorkflowNodeType | None:
        """Resolve a machine-key (e.g. 'source_url') to a workflow_node_type row."""
        result = await self.db.execute(
            select(WorkflowNodeType).where(WorkflowNodeType.type == type_key)
        )
        return result.scalar_one_or_none()

    async def list_node_types(self) -> list[WorkflowNodeType]:
        result = await self.db.execute(
            select(WorkflowNodeType)
            .where(WorkflowNodeType.is_deleted == False)  # noqa: E712
            .order_by(WorkflowNodeType.type.asc())
        )
        return list(result.scalars().all())

    # ── projection rows ───────────────────────────────────────────────────

    async def list_node_instances(self, workflow_id: str) -> list[WorkflowNodeInstance]:
        result = await self.db.execute(
            select(WorkflowNodeInstance).where(
                WorkflowNodeInstance.workflow_id == workflow_id,
                WorkflowNodeInstance.is_deleted == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def list_edge_instances(self, workflow_id: str) -> list[WorkflowEdgeInstance]:
        result = await self.db.execute(
            select(WorkflowEdgeInstance).where(
                WorkflowEdgeInstance.workflow_id == workflow_id,
                WorkflowEdgeInstance.is_deleted == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def replace_projections(
        self,
        workflow_id: str,
        nodes: list[WorkflowNodeInstance],
        edges: list[WorkflowEdgeInstance],
    ) -> None:
        """Atomic replace: drop all node+edge rows for the workflow, insert new.

        Order matters — edges reference nodes via FK. Delete edges first, then
        nodes (deleting nodes would CASCADE the edges anyway, but explicit is
        safer when the txn fails partway through).
        """
        await self.db.execute(
            delete(WorkflowEdgeInstance).where(WorkflowEdgeInstance.workflow_id == workflow_id)
        )
        await self.db.execute(
            delete(WorkflowNodeInstance).where(WorkflowNodeInstance.workflow_id == workflow_id)
        )
        # Flush deletes before the inserts to avoid ID collisions when the
        # client reuses the same wni_/we_ ids across save.
        await self.db.flush()
        for node in nodes:
            self.db.add(node)
        await self.db.flush()
        for edge in edges:
            self.db.add(edge)
        await self.db.flush()
