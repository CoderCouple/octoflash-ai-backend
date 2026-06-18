"""Repository for YouTube ingest cooldowns and attempt windows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.youtube_ingest_guard_model import YoutubeIngestGuard


class YoutubeIngestGuardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, scope: str, key: str) -> YoutubeIngestGuard | None:
        result = await self.db.execute(
            select(YoutubeIngestGuard).where(
                YoutubeIngestGuard.scope == scope,
                YoutubeIngestGuard.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def get_active(self, scope: str, key: str) -> YoutubeIngestGuard | None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(YoutubeIngestGuard).where(
                YoutubeIngestGuard.scope == scope,
                YoutubeIngestGuard.key == key,
                YoutubeIngestGuard.blocked_until.is_not(None),
                YoutubeIngestGuard.blocked_until > now,
            )
        )
        return result.scalar_one_or_none()

    async def record_block(
        self,
        *,
        scope: str,
        key: str,
        reason: str,
        cooldown: timedelta,
        source_url: str | None = None,
        detail: str | None = None,
    ) -> YoutubeIngestGuard:
        now = datetime.now(timezone.utc)
        row = await self.get(scope, key)
        if row is None:
            row = YoutubeIngestGuard(scope=scope, key=key)
            self.db.add(row)

        row.reason = reason
        row.source_url = source_url
        row.detail = detail[:2000] if detail else None
        row.blocked_until = now + cooldown
        row.updated_at = now
        await self.db.flush()
        return row

    async def record_user_attempt(
        self,
        *,
        user_id: str,
        limit: int,
        window: timedelta,
    ) -> YoutubeIngestGuard:
        now = datetime.now(timezone.utc)
        row = await self.get("user", user_id)
        if row is None:
            row = YoutubeIngestGuard(
                scope="user",
                key=user_id,
                reason="attempt_window",
                attempts_count=0,
                window_started_at=now,
            )
            self.db.add(row)

        if not row.window_started_at or row.window_started_at <= now - window:
            row.attempts_count = 0
            row.window_started_at = now
            if row.reason == "server_attempt_limit":
                row.blocked_until = None

        row.attempts_count = int(row.attempts_count or 0) + 1
        row.reason = "server_attempt_limit" if row.attempts_count > limit else "attempt_window"
        if row.attempts_count > limit:
            row.blocked_until = (row.window_started_at or now) + window
        row.updated_at = now
        await self.db.flush()
        return row
