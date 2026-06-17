"""Source (input library) API controller.

  GET    /sources                → list user's sources
  GET    /sources/{id}           → source + recent videos
  POST   /sources                → create
  PATCH  /sources/{id}           → partial update
  DELETE /sources/{id}           → soft delete
  POST   /sources/{id}/sync      → refresh videos via the platform fetcher (stubbed)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.source_request import CreateSourceRequest, UpdateSourceRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.source_response import SourceDetailResponse, SourceResponse
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.common.pagination import PaginatedResponse
from app.db.session import get_db
from app.service.source_service import SourceService

router = APIRouter(tags=[Tags.Source])


def get_source_service(db: AsyncSession = Depends(get_db)) -> SourceService:
    return SourceService(db)


@router.get(
    "/sources",
    response_model=BaseResponse[PaginatedResponse[SourceResponse]],
)
async def list_sources(
    ctx: UserContext = Depends(get_user_context_or_default),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service: SourceService = Depends(get_source_service),
):
    items, total = await service.list(ctx.user_id, offset, limit)
    page = PaginatedResponse(items=items, total=total, offset=offset, limit=limit)
    return success_response(page, "Sources fetched")


@router.get(
    "/sources/{source_id}",
    response_model=BaseResponse[SourceDetailResponse],
)
async def get_source(
    source_id: str,
    video_limit: int = Query(default=50, ge=1, le=500),
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SourceService = Depends(get_source_service),
):
    result = await service.get_detail(
        source_id, user_id=ctx.user_id, video_limit=video_limit,
    )
    return success_response(result, "Source fetched")


@router.post(
    "/sources",
    response_model=BaseResponse[SourceResponse],
    status_code=201,
)
async def create_source(
    body: CreateSourceRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SourceService = Depends(get_source_service),
):
    result = await service.create(body, user_id=ctx.user_id)
    return success_response(result, "Source created", 201)


@router.patch(
    "/sources/{source_id}",
    response_model=BaseResponse[SourceResponse],
)
async def update_source(
    source_id: str,
    body: UpdateSourceRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SourceService = Depends(get_source_service),
):
    result = await service.update(source_id, user_id=ctx.user_id, body=body)
    return success_response(result, "Source updated")


@router.delete("/sources/{source_id}", response_model=BaseResponse)
async def delete_source(
    source_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SourceService = Depends(get_source_service),
):
    await service.delete(source_id, user_id=ctx.user_id)
    return success_response(None, "Source deleted")


@router.post("/sources/{source_id}/sync", response_model=BaseResponse)
async def sync_source(
    source_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: SourceService = Depends(get_source_service),
):
    """Re-fetch recent videos for the source. 501 until the YouTube fetcher lands."""
    await service.sync_videos(source_id, user_id=ctx.user_id)
    return success_response(None, "Source synced")
