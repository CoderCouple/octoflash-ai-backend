"""Target (publishing destination) API controller.

  GET    /targets                       → list user's targets
  GET    /targets/{id}                  → one target (no OAuth blob)
  POST   /targets                       → create (optionally with inline OAuth blob)
  PATCH  /targets/{id}                  → partial update + credential rotation
  DELETE /targets/{id}                  → soft delete
  GET    /targets/oauth/{platform}/authorize  → OAuth authorize URL (FE redirects browser there)

The matching public callback (no JWT) lives in `oauth_callback_api.py`,
mounted at root because OAuth providers won't carry the bearer token.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.publish_request import PublishTargetRequest
from app.api.v1.request.target_request import CreateTargetRequest, UpdateTargetRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.target_response import TargetResponse
from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.common.enum.target import TargetPlatform
from app.common.pagination import PaginatedResponse
from app.db.session import get_db
from app.common.oauth import get_redirect_uri
from app.service.oauth_service import (
    OAuthNotConfiguredError,
    OAuthService,
)
from app.service.publish.models import PublishMetadata
from app.service.publish_service import PublishService
from app.service.target_service import TargetService

router = APIRouter(tags=[Tags.Target])


def get_target_service(db: AsyncSession = Depends(get_db)) -> TargetService:
    return TargetService(db)


class AuthorizeResponse(BaseModel):
    """Returned by GET /targets/oauth/{platform}/authorize."""

    authorize_url: str
    state: str
    redirect_uri: str


@router.get(
    "/targets",
    response_model=BaseResponse[PaginatedResponse[TargetResponse]],
)
async def list_targets(
    ctx: UserContext = Depends(get_user_context_or_default),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    service: TargetService = Depends(get_target_service),
):
    items, total = await service.list(ctx.user_id, offset, limit)
    page = PaginatedResponse(items=items, total=total, offset=offset, limit=limit)
    return success_response(page, "Targets fetched")


@router.get(
    "/targets/{target_id}",
    response_model=BaseResponse[TargetResponse],
)
async def get_target(
    target_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: TargetService = Depends(get_target_service),
):
    result = await service.get(target_id, user_id=ctx.user_id)
    return success_response(result, "Target fetched")


@router.post(
    "/targets",
    response_model=BaseResponse[TargetResponse],
    status_code=201,
)
async def create_target(
    body: CreateTargetRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: TargetService = Depends(get_target_service),
):
    result = await service.create(body, user_id=ctx.user_id)
    return success_response(result, "Target created", 201)


@router.patch(
    "/targets/{target_id}",
    response_model=BaseResponse[TargetResponse],
)
async def update_target(
    target_id: str,
    body: UpdateTargetRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: TargetService = Depends(get_target_service),
):
    result = await service.update(target_id, user_id=ctx.user_id, body=body)
    return success_response(result, "Target updated")


@router.delete("/targets/{target_id}", response_model=BaseResponse)
async def delete_target(
    target_id: str,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: TargetService = Depends(get_target_service),
):
    await service.delete(target_id, user_id=ctx.user_id)
    return success_response(None, "Target deleted")


@router.post(
    "/targets/{target_id}/publish",
    response_model=BaseResponse[WorkflowExecutionResponse],
    status_code=202,
)
async def publish_target(
    target_id: str,
    body: PublishTargetRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    db: AsyncSession = Depends(get_db),
):
    """Upload the project's final render for `orientation` to this target.

    Returns 202 with the WorkflowExecution to poll at GET /executions/{id}.
    Returns 409 if the target has no credential / project hasn't generated
    a final video / target was disconnected. Returns 401 if the stored
    token can't refresh (user must reconnect). Returns 501 if the target's
    platform has no publisher implemented yet.
    """
    # service-side tenant filter is a follow-up.
    metadata = PublishMetadata(
        title=body.title,
        description=body.description,
        tags=body.tags,
        privacy=body.privacy,
        extra=body.extra,
    )
    execution = await PublishService(db).publish(
        target_id=target_id,
        project_id=body.project_id,
        orientation=body.orientation,
        metadata=metadata,
    )
    return success_response(execution, "Publish started", 202)


@router.get(
    "/targets/oauth/{platform}/authorize",
    response_model=BaseResponse[AuthorizeResponse],
)
async def authorize_target(
    platform: TargetPlatform,
    ctx: UserContext = Depends(get_user_context_or_default),
):
    """Build the platform's OAuth authorize URL.

    The FE redirects `window.location` to `authorize_url`. After consent
    the platform redirects to `{oauth_callback_base}/{platform}` with
    `code` + `state` query params; the public callback handler completes
    the flow + redirects back to the FE.

    Returns 501 if the platform's client_id / client_secret env vars
    aren't configured — that's the single point that exposes
    "you forgot to fill in the .env values".
    """
    try:
        url, state = OAuthService().build_authorize_url(
            platform=platform, user_id=ctx.user_id,
        )
    except OAuthNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e),
        )
    return success_response(
        AuthorizeResponse(
            authorize_url=url,
            state=state,
            redirect_uri=get_redirect_uri(platform),
        ),
        "OAuth authorize URL ready",
    )
