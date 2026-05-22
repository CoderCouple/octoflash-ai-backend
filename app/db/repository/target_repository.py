"""Repository for `target` rows (publishing destinations)."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.target_model import Target


class TargetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, target_id: str) -> Target | None:
        result = await self.db.execute(
            select(Target).where(
                Target.id == target_id,
                Target.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[Target], int]:
        base = select(Target).where(
            Target.user_id == user_id,
            Target.is_deleted == False,  # noqa: E712
        )
        count = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = count.scalar() or 0
        result = await self.db.execute(
            base.order_by(Target.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def create(self, target: Target) -> Target:
        self.db.add(target)
        await self.db.flush()
        return target

    async def update(self, target: Target) -> Target:
        target.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return target

    async def soft_delete(self, target: Target) -> Target:
        target.is_deleted = True
        target.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return target
