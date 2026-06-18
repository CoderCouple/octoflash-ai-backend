"""YouTube ingest guardrails.

Tracks short-lived cooldowns and per-user server-attempt windows for the
best-effort server-side YouTube fallback. This keeps anti-bot blocks from
turning into retry storms.
"""

import uuid

from sqlalchemy import TIMESTAMP, Column, Integer, String, Text, UniqueConstraint, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"ytg_{uuid.uuid4()}"


class YoutubeIngestGuard(Base):
    __tablename__ = "youtube_ingest_guard"
    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_youtube_ingest_guard_scope_key"),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    # scope="video" key=<youtube video id>; scope="user" key=<user_id>
    scope = Column(String(20), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    reason = Column(String(80), nullable=False)
    source_url = Column(String(2048), nullable=True)
    detail = Column(Text, nullable=True)
    attempts_count = Column(Integer, nullable=False, default=0)
    window_started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    blocked_until = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
