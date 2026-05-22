"""/workspace — CRUD inside the active organization."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.workspace_request import (
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest,
)
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.workspace_response import WorkspaceResponse
from app.common.auth.auth import UserContext, get_user_context, require_role
from app.common.pagination import PaginatedResponse
from app.db.session import get_db
from app.service.workspace_service import WorkspaceService

router = APIRouter(tags=[Tags.Workspace])


def get_workspace_service(db: AsyncSession = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(db)


@router.post(
    "/workspace",
    response_model=BaseResponse[WorkspaceResponse],
    status_code=201,
)
async def create_workspace(
    body: CreateWorkspaceRequest,
    ctx: UserContext = Depends(require_role("owner", "admin")),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Create a workspace in the active organization."""
    result = await service.create_workspace(
        ctx.organization_id, body.name, body.description, body.slug, ctx.user_id
    )
    return success_response(result, "Workspace created", 201)


@router.get(
    "/workspace",
    response_model=BaseResponse[PaginatedResponse[WorkspaceResponse]],
)
async def list_workspaces(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    ctx: UserContext = Depends(get_user_context),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """List workspaces in the active organization."""
    workspaces, total = await service.list_workspaces(
        ctx.organization_id, offset, limit
    )
    page = PaginatedResponse(
        items=workspaces, total=total, offset=offset, limit=limit
    )
    return success_response(page, "Workspaces fetched")


@router.get(
    "/workspace/{workspace_id}",
    response_model=BaseResponse[WorkspaceResponse],
)
async def get_workspace(
    workspace_id: str,
    _ctx: UserContext = Depends(get_user_context),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Get workspace details."""
    result = await service.get_workspace(workspace_id)
    return success_response(result, "Workspace fetched")


@router.patch(
    "/workspace/{workspace_id}",
    response_model=BaseResponse[WorkspaceResponse],
)
async def update_workspace(
    workspace_id: str,
    body: UpdateWorkspaceRequest,
    ctx: UserContext = Depends(require_role("owner", "admin")),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Update a workspace. Owner/admin only."""
    result = await service.update_workspace(
        workspace_id,
        name=body.name,
        description=body.description,
        actor_id=ctx.user_id,
    )
    return success_response(result, "Workspace updated")


@router.delete("/workspace/{workspace_id}", response_model=BaseResponse)
async def delete_workspace(
    workspace_id: str,
    ctx: UserContext = Depends(require_role("owner", "admin")),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Soft-delete a workspace. Owner/admin only."""
    await service.delete_workspace(workspace_id, ctx.user_id)
    return success_response(None, "Workspace deleted")
