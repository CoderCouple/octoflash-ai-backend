"""/me — current user profile + active org/workspace context + preferences."""

import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
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
from app.settings import settings

logger = logging.getLogger(__name__)

# Avatar upload constraints — keep in lockstep with FE settings page.
_MAX_AVATAR_BYTES = 8 * 1024 * 1024  # 8 MB
_ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_AVATAR_EXT_BY_TYPE = {
    "image/jpeg": "jpg",
    "image/png":  "png",
    "image/webp": "webp",
    "image/gif":  "gif",
}

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


@router.post("/me/avatar", response_model=BaseResponse[UserResponse])
async def upload_avatar(
    request: Request,
    file: UploadFile,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: UserService = Depends(get_user_service),
):
    """Upload an avatar image. Returns the updated user with the new
    avatar_url already set.

    Storage is local disk in dev (`{local_storage_path}/avatars/*`,
    served at /storage/avatars/*). In prod, when `S3_PUBLIC_BASE_URL`
    is configured, swap the write target to S3 — the public URL
    contract is the same.

    The companion PATCH /me endpoint still accepts an `avatar_url`
    directly, so users who'd rather paste a Gravatar / GitHub URL
    skip this endpoint entirely.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Avatar must be one of: {sorted(_ALLOWED_AVATAR_TYPES)}. Got: {content_type!r}",
        )

    # Read once + size-check. FastAPI streams the upload via SpooledTemporaryFile
    # so reading the whole thing into memory is fine at the 8 MB cap.
    data = await file.read()
    if len(data) > _MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Avatar must be ≤ {_MAX_AVATAR_BYTES // (1024*1024)} MB.",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty upload.",
        )

    ext = _AVATAR_EXT_BY_TYPE[content_type]
    # New filename per upload so the FE/cdn caches don't serve a stale image.
    fname = f"{ctx.user_id}-{int(time.time())}-{uuid.uuid4().hex[:8]}.{ext}"
    storage_root = Path(settings.local_storage_path or "storage").resolve()
    dest = storage_root / "avatars" / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    logger.info("avatar upload: user=%s path=%s bytes=%d", ctx.user_id, dest, len(data))

    # Build the public URL. In prod with S3_PUBLIC_BASE_URL configured we'd
    # have uploaded to S3 above and use `{s3_public_base_url}/avatars/{fname}`;
    # in dev we serve from this same FastAPI host via the /storage mount.
    if settings.s3_public_base_url:
        avatar_url = f"{settings.s3_public_base_url.rstrip('/')}/avatars/{fname}"
    else:
        avatar_url = str(request.url_for("storage", path=f"avatars/{fname}"))

    await service.update_profile(ctx.user_id, avatar_url=avatar_url)
    return success_response(
        await _build_user_response(service, ctx.user_id), "Avatar uploaded"
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
