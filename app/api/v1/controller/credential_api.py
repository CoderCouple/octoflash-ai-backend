"""/credentials — per-user secret vault.

Surfaces the env-pinned keys (ANTHROPIC_API_KEY, ELEVEN_API_KEY,
TEMPORAL_API_KEY, …) through the settings UI. Stored values are encrypted at
rest; the API returns only masked previews so the raw secret never leaves the
server once written.

Routes:
   GET    /credentials              → list this user's vault entries (masked)
   PUT    /credentials/{name}       → create or update by name
   DELETE /credentials/{name}       → soft-delete
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tags import Tags
from app.api.v1.request.credential_request import UpsertCredentialRequest
from app.api.v1.response.base_response import BaseResponse, success_response
from app.api.v1.response.credential_response import CredentialResponse
from app.common.auth.auth import UserContext, get_user_context
from app.db.session import get_db
from app.service.credential_service import CredentialService

router = APIRouter(tags=[Tags.Credential])


def get_credential_service(db: AsyncSession = Depends(get_db)) -> CredentialService:
    return CredentialService(db)


@router.get("/credentials", response_model=BaseResponse[list[CredentialResponse]])
async def list_credentials(
    ctx: UserContext = Depends(get_user_context),
    service: CredentialService = Depends(get_credential_service),
):
    rows = await service.list_for_user(ctx.user_id)
    return success_response(
        [CredentialResponse(**row) for row in rows], "Credentials fetched"
    )


@router.put(
    "/credentials/{name}", response_model=BaseResponse[CredentialResponse]
)
async def upsert_credential(
    name: str,
    body: UpsertCredentialRequest,
    ctx: UserContext = Depends(get_user_context),
    service: CredentialService = Depends(get_credential_service),
):
    try:
        row = await service.upsert(ctx.user_id, name=name, value=body.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return success_response(CredentialResponse(**row), "Credential saved")


@router.delete(
    "/credentials/{name}", response_model=BaseResponse[None], status_code=200
)
async def delete_credential(
    name: str,
    ctx: UserContext = Depends(get_user_context),
    service: CredentialService = Depends(get_credential_service),
):
    deleted = await service.delete(ctx.user_id, name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")
    return success_response(None, "Credential deleted")
