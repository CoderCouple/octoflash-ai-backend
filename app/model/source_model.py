"""Source — a creator channel the user has saved as INPUT material.

Renamed from `channel` to make the input/output split explicit:
  Source = "pull source content FROM here" (e.g. another creator's YouTube channel)
  Target = "publish the final video TO here" (e.g. user's own YouTube/TikTok/IG)
"""

import uuid

from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Column, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func

from app.common.enum.source import SourcePlatform
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"src_{uuid.uuid4()}"


class Source(Base):
    __tablename__ = "source"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    user_id = Column(String(), ForeignKey("user.id"), nullable=False, index=True)
    platform = Column(
        SAEnum(
            SourcePlatform,
            name="source_platform_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=SourcePlatform.YOUTUBE,
    )
    source_url = Column(Text(), nullable=False)
    external_id = Column(String(128), nullable=True, index=True)
    handle = Column(String(128), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text(), nullable=True)
    thumbnail_url = Column(Text(), nullable=True)
    subscriber_count = Column(BigInteger, nullable=True)
    accent_color = Column(String(16), nullable=True)
    last_synced_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
