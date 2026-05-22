"""Repository for `source` rows (renamed from channel)."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.source_model import Source


class SourceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, source_id: str) -> Source | None:
        result = await self.db.execute(
            select(Source).where(
                Source.id == source_id,
                Source.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[Source], int]:
        base = select(Source).where(
            Source.user_id == user_id,
            Source.is_deleted == False,  # noqa: E712
        )
        count = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = count.scalar() or 0
        result = await self.db.execute(
            base.order_by(Source.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def create(self, source: Source) -> Source:
        self.db.add(source)
        await self.db.flush()
        return source

    async def update(self, source: Source) -> Source:
        source.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return source

    async def soft_delete(self, source: Source) -> Source:
        source.is_deleted = True
        source.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return source
