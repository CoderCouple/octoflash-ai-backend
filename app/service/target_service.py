"""TargetService — CRUD over publishing destinations.

Target = a user's connected publishing account (YouTube/TikTok/Instagram).
Each target has at most one Credential row (1:1) holding the OAuth blob.

The OAuth blob itself never crosses the wire — `TargetResponse.has_credential`
is the FE-visible flag. Real OAuth callback handlers per platform land in a
follow-up task.
"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.request.target_request import CreateTargetRequest, UpdateTargetRequest
from app.api.v1.response.target_response import TargetResponse
from app.common.enum.target import TargetStatus
from app.common.exceptions import EntityNotFoundError
from app.db.repository.credential_repository import CredentialRepository
from app.db.repository.target_repository import TargetRepository
from app.model.credential_model import Credential
from app.model.target_model import Target
from app.settings import settings


class TargetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.target_repo = TargetRepository(db)
        self.credential_repo = CredentialRepository(db)

    async def list(
        self, user_id: str | None = None, offset: int = 0, limit: int = 50
    ) -> tuple[list[TargetResponse], int]:
        targets, total = await self.target_repo.list_for_user(
            user_id or settings.default_user_id, offset, limit
        )
        return [self._to_response(t) for t in targets], total

    async def get(self, target_id: str) -> TargetResponse:
        target = await self.target_repo.get_by_id(target_id)
        if target is None:
            raise EntityNotFoundError("Target", target_id)
        return self._to_response(target)

    async def create(
        self, body: CreateTargetRequest, user_id: str | None = None
    ) -> TargetResponse:
        owner = user_id or settings.default_user_id

        credential_id: str | None = None
        if body.credential_value is not None:
            credential = await self.credential_repo.create(
                Credential(
                    user_id=owner,
                    name=f"{body.platform.value}:{body.handle or body.external_id or 'oauth'}",
                    value=body.credential_value,
                )
            )
            credential_id = credential.id

        target = Target(
            user_id=owner,
            platform=body.platform,
            handle=body.handle,
            external_id=body.external_id,
            display_name=body.display_name,
            avatar_url=body.avatar_url,
            status=TargetStatus.ACTIVE,
            credential_id=credential_id,
            connected_at=datetime.now(timezone.utc) if credential_id else None,
        )
        target = await self.target_repo.create(target)
        return self._to_response(target)

    async def update(self, target_id: str, body: UpdateTargetRequest) -> TargetResponse:
        target = await self.target_repo.get_by_id(target_id)
        if target is None:
            raise EntityNotFoundError("Target", target_id)

        for field in ("handle", "display_name", "avatar_url"):
            value = getattr(body, field)
            if value is not None:
                setattr(target, field, value)
        if body.status is not None:
            target.status = body.status
            if body.status == TargetStatus.DISCONNECTED:
                target.disconnected_at = datetime.now(timezone.utc)

        # Credential rotation paths:
        #   credential_id     → re-point at an existing credential row
        #   credential_value  → rotate the blob on the attached cred, or create one
        if body.credential_id is not None:
            cred = await self.credential_repo.get_by_id(body.credential_id)
            if cred is None:
                raise EntityNotFoundError("Credential", body.credential_id)
            target.credential_id = cred.id
            target.connected_at = datetime.now(timezone.utc)
        elif body.credential_value is not None:
            if target.credential_id is not None:
                cred = await self.credential_repo.get_by_id(target.credential_id)
                if cred is not None:
                    cred.value = body.credential_value
                    await self.credential_repo.update(cred)
            else:
                cred = await self.credential_repo.create(
                    Credential(
                        user_id=target.user_id,
                        name=f"{target.platform.value}:{target.handle or target.external_id or 'oauth'}",
                        value=body.credential_value,
                    )
                )
                target.credential_id = cred.id
                target.connected_at = datetime.now(timezone.utc)

        target = await self.target_repo.update(target)
        return self._to_response(target)

    async def delete(self, target_id: str) -> None:
        target = await self.target_repo.get_by_id(target_id)
        if target is None:
            raise EntityNotFoundError("Target", target_id)
        await self.target_repo.soft_delete(target)

    @staticmethod
    def _to_response(target: Target) -> TargetResponse:
        return TargetResponse.model_validate(
            {
                **{
                    col: getattr(target, col)
                    for col in (
                        "id", "user_id", "platform", "external_id", "handle",
                        "display_name", "avatar_url", "status", "credential_id",
                        "connected_at", "disconnected_at", "last_synced_at",
                        "is_deleted", "created_at", "updated_at",
                    )
                },
                "has_credential": target.credential_id is not None,
            }
        )
