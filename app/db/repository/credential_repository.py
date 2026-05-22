"""Repository for `credential` rows (OAuth blobs + future generic secrets)."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.credential_model import Credential


class CredentialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, credential_id: str) -> Credential | None:
        result = await self.db.execute(
            select(Credential).where(
                Credential.id == credential_id,
                Credential.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[Credential]:
        result = await self.db.execute(
            select(Credential)
            .where(
                Credential.user_id == user_id,
                Credential.is_deleted == False,  # noqa: E712
            )
            .order_by(Credential.name)
        )
        return list(result.scalars().all())

    async def get_by_user_and_name(self, user_id: str, name: str) -> Credential | None:
        result = await self.db.execute(
            select(Credential).where(
                Credential.user_id == user_id,
                Credential.name == name,
                Credential.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def create(self, credential: Credential) -> Credential:
        self.db.add(credential)
        await self.db.flush()
        return credential

    async def update(self, credential: Credential) -> Credential:
        credential.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return credential

    async def soft_delete(self, credential: Credential) -> Credential:
        credential.is_deleted = True
        credential.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return credential
