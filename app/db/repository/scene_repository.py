from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.scene_model import Scene


class SceneRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, scene_id: str) -> Scene | None:
        result = await self.db.execute(select(Scene).where(Scene.id == scene_id))
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: str) -> list[Scene]:
        result = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.n.asc())
        )
        return list(result.scalars().all())

    async def next_n_for_project(self, project_id: str) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(Scene.n), 0) + 1).where(
                Scene.project_id == project_id
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
