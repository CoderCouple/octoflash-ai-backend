from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.channel_video_model import ChannelVideo


class ChannelVideoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_channel(
        self,
        channel_id: str,
        kind: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[ChannelVideo], int]:
        base = select(ChannelVideo).where(ChannelVideo.channel_id == channel_id)
        if kind is not None:
            base = base.where(ChannelVideo.kind == kind)

        total_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = total_result.scalar() or 0

        rows = await self.db.execute(
            base.order_by(ChannelVideo.published_at.desc().nullslast())
            .offset(offset)
            .limit(limit)
        )
        return list(rows.scalars().all()), total

    async def upsert_many(
        self, channel_id: str, videos: list[dict]
    ) -> int:
        """Upsert a batch of (channel_id, external_id)-keyed videos.

        On conflict we refresh the mutable fields (title, views, etc.) — the
        external_id + channel_id stay stable. Returns count of rows touched.
        """
        if not videos:
            return 0

        payloads = [
            {
                "channel_id": channel_id,
                "external_id": v["external_id"],
                "source_url": v["source_url"],
                "title": v["title"],
                "description": v.get("description"),
                "thumbnail_url": v.get("thumbnail_url"),
                "kind": v.get("kind", "landscape"),
                "duration_seconds": v.get("duration_seconds"),
                "view_count": v.get("view_count"),
                "published_at": v.get("published_at"),
            }
            for v in videos
        ]
        stmt = pg_insert(ChannelVideo).values(payloads)
        update_cols = {
            "title": stmt.excluded.title,
            "description": stmt.excluded.description,
            "thumbnail_url": stmt.excluded.thumbnail_url,
            "kind": stmt.excluded.kind,
            "duration_seconds": stmt.excluded.duration_seconds,
            "view_count": stmt.excluded.view_count,
            "published_at": stmt.excluded.published_at,
            "fetched_at": func.now(),
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_channel_video_external_id",
            set_=update_cols,
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount or 0
