"""
A creator's channel (YouTube for v1; `platform` reserved for future others).

Created by the user pasting a channel URL. Metadata is fetched inline at create
time; the video list is fetched inline as a separate /sync call (or as part of
create depending on the endpoint shape).
"""

import uuid

from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Column, String, Text, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"ch_{uuid.uuid4()}"


class Channel(Base):
    __tablename__ = "channel"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)

    # "youtube" for v1. Reserved for vimeo/twitch/etc later.
    platform = Column(String(32), nullable=False, default="youtube")

    # The URL the user originally pasted — kept verbatim for audit + re-sync.
    source_url = Column(Text(), nullable=False)

    # Platform-side identifiers. external_id is the canonical id we hit the API
    # with (e.g. YouTube channel id "UCxxx"); handle is the @username if known.
    external_id = Column(String(128), nullable=True, index=True)
    handle = Column(String(128), nullable=True)

    name = Column(String(255), nullable=False)
    description = Column(Text(), nullable=True)
    thumbnail_url = Column(Text(), nullable=True)
    subscriber_count = Column(BigInteger, nullable=True)

    # Cosmetic — populated by the FE or computed. Useful for sidebar accents.
    accent_color = Column(String(16), nullable=True)

    last_synced_at = Column(TIMESTAMP(timezone=True), nullable=True)
    owner_id = Column(String(), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
