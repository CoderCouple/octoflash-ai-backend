"""UserPreferenceRepository — read / merge the per-user JSONB blob.

Thin data-access layer: stores and returns plain dicts. Pydantic validation
happens in the service layer (`UserPreferences`). Merge is a shallow
overwrite at the top level — fits the current flat shape; revisit if/when
preferences become nested.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user_preference_model import UserPreference


class UserPreferenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, user_id: str) -> dict[str, Any]:
        """Return the user's prefs blob (empty dict if no row)."""
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return dict(row.prefs) if row and row.prefs else {}

    async def merge(
        self, user_id: str, partial: dict[str, Any]
    ) -> dict[str, Any]:
        """Shallow-merge `partial` into the user's prefs blob (UPSERT).

        Keys present in `partial` overwrite (including explicit `None` to
        clear a value). Keys not in `partial` are preserved.
        """
        current = await self.get(user_id)
        merged = {**current, **partial}
        now = datetime.now(timezone.utc)
        stmt = pg_insert(UserPreference).values(
            user_id=user_id,
            prefs=merged,
            updated_at=now,
        ).on_conflict_do_update(
            index_elements=[UserPreference.user_id],
            set_={"prefs": merged, "updated_at": now},
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return merged
