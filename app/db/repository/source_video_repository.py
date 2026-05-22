"""Repository for `source_video` rows."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.source_video_model import SourceVideo


class SourceVideoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_source(
        self, source_id: str, offset: int = 0, limit: int = 50
    ) -> list[SourceVideo]:
        result = await self.db.execute(
            select(SourceVideo)
            .where(SourceVideo.source_id == source_id)
            .order_by(SourceVideo.published_at.desc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def upsert_many(self, videos: list[SourceVideo]) -> int:
        """Bulk upsert by (source_id, external_id) — returns count of rows touched.

        Uses Postgres `ON CONFLICT DO UPDATE` so re-syncing a source refreshes
        title/view_count/etc. without duplicating rows.
        """
        if not videos:
            return 0
        rows = [
            {
                "id": v.id,
                "source_id": v.source_id,
                "external_id": v.external_id,
                "source_url": v.source_url,
                "title": v.title,
                "description": v.description,
                "thumbnail_url": v.thumbnail_url,
                "kind": v.kind,
                "duration_seconds": v.duration_seconds,
                "view_count": v.view_count,
                "published_at": v.published_at,
            }
            for v in videos
        ]
        stmt = insert(SourceVideo).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_source_video_external_id",
            set_={
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "thumbnail_url": stmt.excluded.thumbnail_url,
                "duration_seconds": stmt.excluded.duration_seconds,
                "view_count": stmt.excluded.view_count,
                "published_at": stmt.excluded.published_at,
            },
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return len(rows)
