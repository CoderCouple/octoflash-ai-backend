"""Template catalog API — read-only."""

from fastapi import APIRouter, Depends

from app.api.tags import Tags
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.template_response import (
    TemplateDetailResponse,
    TemplateSummaryResponse,
)
from app.service.template_service import TemplateService

router = APIRouter(tags=[Tags.Template])


def get_template_service() -> TemplateService:
    return TemplateService()


@router.get("/templates", response_model=BaseResponse[list[TemplateSummaryResponse]])
async def list_templates(service: TemplateService = Depends(get_template_service)):
    """The full 127-template catalog. Lightweight — definitions are not loaded.

    `implemented: false` means the template exists in the catalog but its
    `app/templates/defs/<id>.py` file hasn't been written yet — the frontend
    should grey it out in the library UI.
    """
    return success_response(service.list_templates(), "Templates fetched")


@router.get(
    "/templates/{template_id}",
    response_model=BaseResponse[TemplateDetailResponse],
)
async def get_template(
    template_id: str,
    service: TemplateService = Depends(get_template_service),
):
    """Full TemplateDefinition for one template, including params + steps +
    style modifiers + content hash. 404 if the template isn't in the catalog
    or hasn't been implemented yet.
    """
    return success_response(service.get_template_detail(template_id), "Template fetched")
