from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.project_model import Project


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: str) -> Project | None:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        user_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        org_id: str | None = None,
        workspace_id: str | None = None,
    ) -> tuple[list[Project], int]:
        base = select(Project).where(Project.is_deleted == False)  # noqa: E712
        if user_id is not None:
            base = base.where(Project.user_id == user_id)
        if org_id is not None:
            base = base.where(Project.org_id == org_id)
        if workspace_id is not None:
            base = base.where(Project.workspace_id == workspace_id)

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            base.order_by(Project.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_by_workspace(
        self, workspace_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[Project], int]:
        return await self.list_all(
            workspace_id=workspace_id, offset=offset, limit=limit
        )

    async def create(self, project: Project) -> Project:
        self.db.add(project)
        await self.db.flush()
        return project

    async def update(self, project: Project) -> Project:
        await self.db.flush()
        return project

    async def soft_delete(self, project: Project) -> Project:
        project.is_deleted = True
        project.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return project
