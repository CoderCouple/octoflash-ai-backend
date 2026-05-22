"""Per-user credential vault.

Stores arbitrary `(name, value)` secrets — used to surface the same keys that
otherwise live in `.env` (ANTHROPIC_API_KEY, ELEVEN_API_KEY, TEMPORAL_API_KEY,
…) through the settings UI. Values are encrypted at rest via
`app.common.security.secret_crypto.Fernet`; the API only ever returns a
masked preview so the raw secret never leaves the server once written.

Resolution order at request time is up to each caller (see `resolve_secret`):
DB value if set, else fall back to the static `settings.*_api_key`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.secret_crypto import decrypt, encrypt, mask
from app.db.repository.credential_repository import CredentialRepository
from app.model.credential_model import Credential


class CredentialService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CredentialRepository(db)

    async def list_for_user(self, user_id: str) -> list[dict]:
        """Return masked credentials the user has stored — never raw values."""
        rows = await self.repo.list_by_user(user_id)
        out: list[dict] = []
        for row in rows:
            raw = decrypt(row.value)
            out.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "masked_value": mask(raw),
                    "is_set": bool(raw),
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
            )
        return out

    async def upsert(self, user_id: str, name: str, value: str) -> dict:
        """Create or update a credential by `(user_id, name)`. Returns the
        masked view, same shape as list_for_user."""
        name = name.strip()
        if not name:
            raise ValueError("Credential name is required")
        existing = await self.repo.get_by_user_and_name(user_id, name)
        encrypted = encrypt(value)
        if existing is None:
            cred = Credential(
                user_id=user_id,
                name=name,
                value=encrypted,
                created_by=user_id,
                updated_by=user_id,
            )
            await self.repo.create(cred)
        else:
            existing.value = encrypted
            existing.updated_by = user_id
            await self.repo.update(existing)
            cred = existing
        await self.db.commit()
        return {
            "id": cred.id,
            "name": cred.name,
            "masked_value": mask(value),
            "is_set": bool(value),
            "created_at": cred.created_at,
            "updated_at": cred.updated_at,
        }

    async def delete(self, user_id: str, name: str) -> bool:
        existing = await self.repo.get_by_user_and_name(user_id, name)
        if existing is None:
            return False
        await self.repo.soft_delete(existing)
        await self.db.commit()
        return True

    async def resolve_secret(self, user_id: str, name: str) -> str | None:
        """Used by render-path services that want a per-user override of an
        env-pinned key. Returns the decrypted value or None if unset."""
        row = await self.repo.get_by_user_and_name(user_id, name)
        if row is None:
            return None
        return decrypt(row.value) or None
