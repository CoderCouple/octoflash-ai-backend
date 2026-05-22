from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.workspace_model import Workspace


class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        result = await self.db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_by_org_and_slug(self, org_id: str, slug: str) -> Workspace | None:
        result = await self.db.execute(
            select(Workspace).where(
                Workspace.org_id == org_id,
                Workspace.slug == slug,
                Workspace.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self, org_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[Workspace], int]:
        base = select(Workspace).where(
            Workspace.org_id == org_id,
            Workspace.is_deleted == False,  # noqa: E712
        )
        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            base.order_by(Workspace.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def count_by_org(self, org_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Workspace)
            .where(
                Workspace.org_id == org_id,
                Workspace.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar() or 0

    async def create(self, workspace: Workspace) -> Workspace:
        self.db.add(workspace)
        await self.db.flush()
        return workspace

    async def update(self, workspace: Workspace) -> Workspace:
        await self.db.flush()
        return workspace

    async def soft_delete(
        self, workspace: Workspace, actor_id: str | None = None
    ) -> Workspace:
        workspace.is_deleted = True
        workspace.updated_by = actor_id
        workspace.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return workspace
