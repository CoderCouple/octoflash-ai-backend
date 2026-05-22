from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enum.scene import Orientation
from app.model.scene_model import Scene


class SceneRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, scene_id: str) -> Scene | None:
        result = await self.db.execute(select(Scene).where(Scene.id == scene_id))
        return result.scalar_one_or_none()

    async def list_by_project(
        self, project_id: str, orientation: Orientation | str | None = None
    ) -> list[Scene]:
        """List scenes for a project. When `orientation` is set, scope to that
        orientation only — needed by the ffmpeg concat path and the per-orientation
        generate workflow."""
        stmt = select(Scene).where(Scene.project_id == project_id)
        if orientation is not None:
            stmt = stmt.where(Scene.orientation == orientation)
        stmt = stmt.order_by(Scene.n.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def next_n_for_project(
        self, project_id: str, orientation: Orientation | str = Orientation.PORTRAIT
    ) -> int:
        """Next free `n` slot scoped to (project_id, orientation) — the unique
        constraint is on the triple, so n=1..N exists separately per orientation."""
        result = await self.db.execute(
            select(func.coalesce(func.max(Scene.n), 0) + 1).where(
                Scene.project_id == project_id,
                Scene.orientation == orientation,
            )
        )
        return result.scalar() or 1

    async def create(self, scene: Scene) -> Scene:
        self.db.add(scene)
        await self.db.flush()
        return scene

    async def update(self, scene: Scene) -> Scene:
        await self.db.flush()
        return scene

    async def delete(self, scene: Scene) -> None:
        await self.db.delete(scene)
        await self.db.flush()
