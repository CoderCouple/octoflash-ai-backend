"""SourceService — CRUD over the input library.

Source = a creator channel the user has saved as input material (e.g. a
YouTube channel they pull source content FROM). Distinct from Target,
which is publishing destinations.

The sync flow (POST /sources/:id/sync) is stubbed pending the YouTube
fetcher rewrite.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.request.source_request import CreateSourceRequest, UpdateSourceRequest
from app.api.v1.response.source_response import (
    SourceDetailResponse,
    SourceResponse,
    SourceVideoResponse,
)
from app.common.exceptions import EntityNotFoundError
from app.db.repository.source_repository import SourceRepository
from app.db.repository.source_video_repository import SourceVideoRepository
from app.model.source_model import Source
from app.settings import settings


class SourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.source_repo = SourceRepository(db)
        self.video_repo = SourceVideoRepository(db)

    async def list(
        self, user_id: str | None = None, offset: int = 0, limit: int = 50
    ) -> tuple[list[SourceResponse], int]:
        sources, total = await self.source_repo.list_for_user(
            user_id or settings.default_user_id, offset, limit
        )
        return [SourceResponse.model_validate(s) for s in sources], total

    async def get_detail(self, source_id: str, video_limit: int = 50) -> SourceDetailResponse:
        source = await self.source_repo.get_by_id(source_id)
        if source is None:
            raise EntityNotFoundError("Source", source_id)
        videos = await self.video_repo.list_for_source(source_id, 0, video_limit)
        return SourceDetailResponse(
            **SourceResponse.model_validate(source).model_dump(),
            videos=[SourceVideoResponse.model_validate(v) for v in videos],
        )

    async def create(
        self, body: CreateSourceRequest, user_id: str | None = None
    ) -> SourceResponse:
        source = Source(
            user_id=user_id or settings.default_user_id,
            platform=body.platform,
            source_url=str(body.source_url),
            external_id=body.external_id,
            handle=body.handle,
            name=body.name,
            description=body.description,
            thumbnail_url=str(body.thumbnail_url) if body.thumbnail_url else None,
            subscriber_count=body.subscriber_count,
            accent_color=body.accent_color,
        )
        source = await self.source_repo.create(source)
        return SourceResponse.model_validate(source)

    async def update(self, source_id: str, body: UpdateSourceRequest) -> SourceResponse:
        source = await self.source_repo.get_by_id(source_id)
        if source is None:
            raise EntityNotFoundError("Source", source_id)
        for field in ("name", "handle", "description", "subscriber_count", "accent_color"):
            value = getattr(body, field)
            if value is not None:
                setattr(source, field, value)
        if body.thumbnail_url is not None:
            source.thumbnail_url = str(body.thumbnail_url)
        source = await self.source_repo.update(source)
        return SourceResponse.model_validate(source)

    async def delete(self, source_id: str) -> None:
        source = await self.source_repo.get_by_id(source_id)
        if source is None:
            raise EntityNotFoundError("Source", source_id)
        await self.source_repo.soft_delete(source)

    async def sync_videos(self, source_id: str) -> None:
        """Fetch fresh videos for the source.

        Stub pending the YouTube fetcher rewrite (currently raises
        NotImplementedError). When wired, this will upsert recent videos via
        SourceVideoRepository.upsert_many and update source.last_synced_at.
        """
        source = await self.source_repo.get_by_id(source_id)
        if source is None:
            raise EntityNotFoundError("Source", source_id)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Source video sync not wired yet — pending YouTube fetcher rewrite.",
        )
        # When wired:
        # videos = fetch_videos(source.external_id)
        # await self.video_repo.upsert_many(videos)
        # source.last_synced_at = datetime.now(timezone.utc)
        # await self.source_repo.update(source)
