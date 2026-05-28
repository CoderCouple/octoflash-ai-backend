"""Waitlist signups — single-table CRUD."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.waitlist_model import WaitlistEntry


class WaitlistRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> WaitlistEntry | None:
        result = await self.db.execute(
            select(WaitlistEntry).where(WaitlistEntry.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, entry: WaitlistEntry) -> WaitlistEntry:
        # Normalize email at the repo boundary so dedupe + lookups stay
        # case-insensitive without sprinkling .lower() through callers.
        entry.email = entry.email.lower()
        self.db.add(entry)
        await self.db.flush()
        return entry
