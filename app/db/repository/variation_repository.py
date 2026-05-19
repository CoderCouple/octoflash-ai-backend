from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.variation_model import Variation


class VariationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, variation_id: str) -> Variation | None:
        result = await self.db.execute(
            select(Variation).where(Variation.id == variation_id)
        )
        return result.scalar_one_or_none()

    async def list_by_scene(self, scene_id: str) -> list[Variation]:
        result = await self.db.execute(
            select(Variation)
            .where(Variation.scene_id == scene_id)
            .order_by(Variation.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, variation: Variation) -> Variation:
        self.db.add(variation)
        await self.db.flush()
        return variation

    async def update(self, variation: Variation) -> Variation:
        await self.db.flush()
        return variation
