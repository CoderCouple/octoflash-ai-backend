"""/me — current user profile + active org/workspace context + preferences."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.user_request import (
    SwitchContextRequest,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
)
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.user_response import (
    UserContextResponse,
    UserPreferences,
    UserResponse,
)
from app.common.auth.auth import UserContext, get_user_context_or_default
from app.db.session import get_db
from app.service.user_service import UserService

router = APIRouter(tags=[Tags.Me])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


async def _build_user_response(
    service: UserService, user_id: str
) -> UserResponse:
    """Load the User row + preferences and combine into the wire shape."""
    user = await service.get_user(user_id)
    prefs = await service.get_preferences(user_id)
    response = UserResponse.model_validate(user)
    response.preferences = prefs
    return response


@router.get("/me", response_model=BaseResponse[UserContextResponse])
async def get_current_user_profile(
    ctx: UserContext = Depends(get_user_context_or_default),
    service: UserService = Depends(get_user_service),
):
    """Return the current user with active org / workspace / role context.

    `user.preferences` is loaded from the `user_preference` satellite table
    in the same request — clients don't need a separate fetch.
    """
    user_resp = await _build_user_response(service, ctx.user_id)
    result = UserContextResponse(
        user=user_resp,
        organization_id=ctx.organization_id,
        workspace_id=ctx.workspace_id,
        role=ctx.role,
    )
    return success_response(result, "User profile fetched")


@router.patch("/me", response_model=BaseResponse[UserResponse])
async def update_current_user_profile(
    body: UpdateProfileRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: UserService = Depends(get_user_service),
):
    """Update display name and/or avatar. Preferences have their own route."""
    await service.update_profile(
        ctx.user_id, display_name=body.display_name, avatar_url=body.avatar_url
    )
    return success_response(
        await _build_user_response(service, ctx.user_id), "Profile updated"
    )


@router.put("/me/context", response_model=BaseResponse[UserResponse])
async def switch_context(
    body: SwitchContextRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: UserService = Depends(get_user_service),
):
    """Switch the active organization and/or workspace."""
    await service.switch_context(
        ctx.user_id, org_id=body.organization_id, workspace_id=body.workspace_id
    )
    return success_response(
        await _build_user_response(service, ctx.user_id), "Context switched"
    )


@router.patch(
    "/me/preferences",
    response_model=BaseResponse[UserPreferences],
)
async def update_preferences(
    body: UpdatePreferencesRequest,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: UserService = Depends(get_user_service),
):
    """Sparse partial update of the user's preferences blob.

    Only keys present in the request body are written; missing keys keep
    their current value. Send `null` to explicitly clear a value.
    """
    # `exclude_unset` is the load-bearing bit: it lets us distinguish
    # "field omitted" (preserve) from "field set to null" (clear).
    partial = body.model_dump(exclude_unset=True)
    prefs = await service.update_preferences(ctx.user_id, partial)
    return success_response(prefs, "Preferences updated")
