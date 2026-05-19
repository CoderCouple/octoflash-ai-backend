"""Variation API — operations on an existing variation."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.variation_request import RerenderVariationRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.job_response import JobResponse
from app.db.session import get_db
from app.service.variation_service import VariationService

router = APIRouter(tags=[Tags.Variation])


def get_variation_service(db: AsyncSession = Depends(get_db)) -> VariationService:
    return VariationService(db)


@router.post(
    "/variations/{variation_id}/render",
    response_model=BaseResponse[JobResponse],
    status_code=202,
)
async def rerender_variation(
    variation_id: str,
    body: RerenderVariationRequest,
    service: VariationService = Depends(get_variation_service),
):
    """Re-render an existing variation (optionally with overridden params)."""
    job = await service.rerender(variation_id, params_override=body.params_override)
    return success_response(job, "Re-render queued", 202)
