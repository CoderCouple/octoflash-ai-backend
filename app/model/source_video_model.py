"""SourceVideo — one video discovered on a Source. Renamed from `channel_video`."""

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
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func

from app.common.enum.source import SourceVideoKind
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"srcv_{uuid.uuid4()}"


class SourceVideo(Base):
    __tablename__ = "source_video"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_source_video_external_id"),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    source_id = Column(String(), ForeignKey("source.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(64), nullable=False)
    source_url = Column(Text(), nullable=False)
    title = Column(Text(), nullable=False)
    description = Column(Text(), nullable=True)
    thumbnail_url = Column(Text(), nullable=True)
    kind = Column(
        SAEnum(
            SourceVideoKind,
            name="source_video_kind_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=SourceVideoKind.LANDSCAPE,
    )
    duration_seconds = Column(Integer, nullable=True)
    view_count = Column(BigInteger, nullable=True)
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)
    fetched_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
