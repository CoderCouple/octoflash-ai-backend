"""
One video discovered on a Channel.

`kind` is one of:
  - "short"     — vertical, < ~60s (YouTube Shorts; URL contains /shorts/)
  - "landscape" — everything else (regular YouTube videos)

We don't store the video bytes; just metadata + the canonical source_url so
the user can hand it to the project pipeline ("use as source") later.
"""

import uuid

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"cv_{uuid.uuid4()}"


class ChannelVideo(Base):
    __tablename__ = "channel_video"
    __table_args__ = (
        # A video should appear at most once per channel.
        UniqueConstraint("channel_id", "external_id", name="uq_channel_video_external_id"),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    channel_id = Column(String(), ForeignKey("channel.id"), nullable=False, index=True)

    external_id = Column(String(64), nullable=False)  # YouTube video id (vXxxx)
    source_url = Column(Text(), nullable=False)       # canonical watch URL

    title = Column(Text(), nullable=False)
    description = Column(Text(), nullable=True)
    thumbnail_url = Column(Text(), nullable=True)

    kind = Column(String(16), nullable=False, default="landscape")  # "short" | "landscape"
    duration_seconds = Column(Integer, nullable=True)
    view_count = Column(BigInteger, nullable=True)
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)

    fetched_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
