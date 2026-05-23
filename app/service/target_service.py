"""TargetService — CRUD over publishing destinations.

Target = a user's connected publishing account (youtube / tiktok /
instagram / linkedin / x). Each target has at most one Credential row
(1:1) holding the encrypted OAuth blob.

The OAuth blob itself never crosses the wire — `TargetResponse.has_credential`
is the FE-visible flag.
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.request.target_request import CreateTargetRequest, UpdateTargetRequest
from app.api.v1.response.target_response import TargetResponse
from app.common.enum.target import TargetPlatform, TargetStatus
from app.common.exceptions import EntityNotFoundError
from app.common.oauth import NormalizedAccount
from app.common.security.secret_crypto import encrypt
from app.db.repository.credential_repository import CredentialRepository
from app.db.repository.target_repository import TargetRepository
from app.model.credential_model import Credential
from app.model.target_model import Target
from app.service.oauth_service import TokenBlob
from app.settings import settings

log = logging.getLogger(__name__)


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
                    value=encrypt(body.credential_value),
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
                    cred.value = encrypt(body.credential_value)
                    await self.credential_repo.update(cred)
            else:
                cred = await self.credential_repo.create(
                    Credential(
                        user_id=target.user_id,
                        name=f"{target.platform.value}:{target.handle or target.external_id or 'oauth'}",
                        value=encrypt(body.credential_value),
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

    async def upsert_from_oauth(
        self,
        *,
        user_id: str,
        platform: TargetPlatform,
        account: NormalizedAccount,
        tokens: TokenBlob,
    ) -> TargetResponse:
        """Land the result of a successful OAuth callback as a Target +
        Credential pair.

        Same (user, platform, external_id) → update the existing rows so a
        reconnect refreshes tokens in place. Different account → new target.
        The credential blob is stored as a Fernet-encrypted JSON document
        carrying access_token, refresh_token, expires_at, scope.
        """
        # 1. Persist (or rotate) the credential blob.
        blob = json.dumps(
            {
                "access_token":  tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "expires_at":    tokens.expires_at.isoformat() if tokens.expires_at else None,
                "scope":         tokens.scope,
                "token_type":    tokens.token_type,
            },
        )
        cred_name = f"{platform.value}:{account.handle or account.external_id}"

        existing_target = await self.target_repo.get_by_user_platform_external(
            user_id=user_id,
            platform=platform,
            external_id=account.external_id,
        )

        if existing_target and existing_target.credential_id:
            cred = await self.credential_repo.get_by_id(existing_target.credential_id)
            if cred is not None:
                cred.value = encrypt(blob)
                cred.name = cred_name
                await self.credential_repo.update(cred)
                credential_id = cred.id
            else:
                # Dangling credential_id (cred was deleted under us) — make a
                # fresh one and rebind.
                cred = await self.credential_repo.create(
                    Credential(user_id=user_id, name=cred_name, value=encrypt(blob)),
                )
                credential_id = cred.id
        else:
            cred = await self.credential_repo.create(
                Credential(user_id=user_id, name=cred_name, value=encrypt(blob)),
            )
            credential_id = cred.id

        # 2. Upsert the Target row.
        now = datetime.now(timezone.utc)
        if existing_target:
            existing_target.handle = account.handle or existing_target.handle
            existing_target.display_name = account.display_name or existing_target.display_name
            existing_target.avatar_url = account.avatar_url or existing_target.avatar_url
            existing_target.status = TargetStatus.ACTIVE
            existing_target.credential_id = credential_id
            existing_target.connected_at = now
            existing_target.disconnected_at = None
            target = await self.target_repo.update(existing_target)
        else:
            target = await self.target_repo.create(
                Target(
                    user_id=user_id,
                    platform=platform,
                    external_id=account.external_id,
                    handle=account.handle,
                    display_name=account.display_name,
                    avatar_url=account.avatar_url,
                    status=TargetStatus.ACTIVE,
                    credential_id=credential_id,
                    connected_at=now,
                ),
            )

        await self.db.commit()
        log.info(
            "TargetService.upsert_from_oauth: target=%s platform=%s user=%s",
            target.id, platform.value, user_id,
        )
        return self._to_response(target)

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
