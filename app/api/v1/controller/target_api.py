"""Target (publishing destination) API controller.

  GET    /targets        → list user's targets
  GET    /targets/{id}   → one target (no OAuth blob)
  POST   /targets        → create (optionally with inline OAuth blob)
  PATCH  /targets/{id}   → partial update + credential rotation
  DELETE /targets/{id}   → soft delete

Per-platform OAuth callback handlers (YouTube/TikTok/Instagram) land in a
later task — they'll call POST /targets internally once tokens are exchanged.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.target_request import CreateTargetRequest, UpdateTargetRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.target_response import TargetResponse
from app.common.pagination import PaginatedResponse
from app.db.session import get_db
from app.service.target_service import TargetService

router = APIRouter(tags=[Tags.Target])


def get_target_service(db: AsyncSession = Depends(get_db)) -> TargetService:
    return TargetService(db)


@router.get(
    "/targets",
    response_model=BaseResponse[PaginatedResponse[TargetResponse]],
)
async def list_targets(
    user_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service: TargetService = Depends(get_target_service),
):
    items, total = await service.list(user_id, offset, limit)
    page = PaginatedResponse(items=items, total=total, offset=offset, limit=limit)
    return success_response(page, "Targets fetched")


@router.get(
    "/targets/{target_id}",
    response_model=BaseResponse[TargetResponse],
)
async def get_target(
    target_id: str,
    service: TargetService = Depends(get_target_service),
):
    result = await service.get(target_id)
    return success_response(result, "Target fetched")


@router.post(
    "/targets",
    response_model=BaseResponse[TargetResponse],
    status_code=201,
)
async def create_target(
    body: CreateTargetRequest,
    service: TargetService = Depends(get_target_service),
):
    result = await service.create(body)
    return success_response(result, "Target created", 201)


@router.patch(
    "/targets/{target_id}",
    response_model=BaseResponse[TargetResponse],
)
async def update_target(
    target_id: str,
    body: UpdateTargetRequest,
    service: TargetService = Depends(get_target_service),
):
    result = await service.update(target_id, body)
    return success_response(result, "Target updated")


@router.delete("/targets/{target_id}", response_model=BaseResponse)
async def delete_target(
    target_id: str,
    service: TargetService = Depends(get_target_service),
):
    await service.delete(target_id)
    return success_response(None, "Target deleted")
