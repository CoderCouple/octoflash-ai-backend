from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.channel_model import Channel


class ChannelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, channel_id: str) -> Channel | None:
        result = await self.db.execute(
            select(Channel).where(
                Channel.id == channel_id,
                Channel.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self, platform: str, external_id: str
    ) -> Channel | None:
        result = await self.db.execute(
            select(Channel).where(
                Channel.platform == platform,
                Channel.external_id == external_id,
                Channel.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self, owner_id: str | None = None, offset: int = 0, limit: int = 50
    ) -> tuple[list[Channel], int]:
        base = select(Channel).where(Channel.is_deleted == False)  # noqa: E712
        if owner_id is not None:
            base = base.where(Channel.owner_id == owner_id)

        total_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = total_result.scalar() or 0

        rows = await self.db.execute(
            base.order_by(Channel.created_at.desc()).offset(offset).limit(limit)
        )
        return list(rows.scalars().all()), total

    async def create(self, channel: Channel) -> Channel:
        self.db.add(channel)
        await self.db.flush()
        return channel

    async def update(self, channel: Channel) -> Channel:
        await self.db.flush()
        return channel

    async def soft_delete(self, channel: Channel) -> Channel:
        channel.is_deleted = True
        channel.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return channel
