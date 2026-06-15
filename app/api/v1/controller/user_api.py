"""/me — current user profile + active org/workspace context + preferences."""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
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
from app.service.supabase_storage_service import (
    BUCKET_AVATARS,
    get_storage_service,
)
from app.service.user_service import UserService

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
    """Load the User row + preferences and combine into the wire shape.

    Translates `avatar_url` from the stored `supabase://<bucket>/<path>`
    sentinel into a fresh signed URL on the way out — never persists a
    time-limited URL on the DB row.
    """
    user = await service.get_user(user_id)
    prefs = await service.get_preferences(user_id)
    response = UserResponse.model_validate(user)
    response.preferences = prefs
    if response.avatar_url and response.avatar_url.startswith("supabase://"):
        rest = response.avatar_url[len("supabase://"):]
        bucket, _, object_path = rest.partition("/")
        try:
            response.avatar_url = get_storage_service().signed_url(bucket, object_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "avatar signed_url failed for user=%s ref=%s: %s",
                user_id, response.avatar_url, exc,
            )
            response.avatar_url = None
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
    file: UploadFile,
    ctx: UserContext = Depends(get_user_context_or_default),
    service: UserService = Depends(get_user_service),
):
    """Upload an avatar image. Returns the updated user with the new
    avatar_url already set.

    Storage is Supabase Storage (`avatars` bucket, private + signed
    URLs, 1h TTL). The companion PATCH /me endpoint still accepts an
    `avatar_url` directly, so users who'd rather paste a Gravatar /
    GitHub URL skip this endpoint entirely.
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

    # Path is per-user so successive uploads overwrite via upsert=true.
    # Filename includes a timestamp + uuid suffix so the CDN treats each
    # version as a new resource (signed URLs already bust caches but it
    # belt-and-suspenders against any prefetch race).
    ext = _AVATAR_EXT_BY_TYPE[content_type]
    path = f"{ctx.user_id}/{int(time.time())}-{uuid.uuid4().hex[:8]}.{ext}"

    try:
        storage = get_storage_service()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    result = storage.upload_bytes(
        bucket=BUCKET_AVATARS, path=path, data=data, content_type=content_type,
    )
    logger.info(
        "avatar upload: user=%s bucket=%s path=%s bytes=%d",
        ctx.user_id, result.bucket, result.path, len(data),
    )

    # Persist a stable virtual reference instead of the time-limited
    # signed URL — `_build_user_response` re-signs on the way out.
    stored_ref = f"supabase://{result.bucket}/{result.path}"
    await service.update_profile(ctx.user_id, avatar_url=stored_ref)
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
