import uuid

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"var_{uuid.uuid4()}"


class Variation(Base):
    __tablename__ = "variation"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    scene_id = Column(String(), ForeignKey("scene.id"), nullable=False, index=True)
    params_snapshot = Column(JSONB, nullable=False, default=dict)
    video_url = Column(Text(), nullable=True)
    audio_url = Column(Text(), nullable=True)
    duration = Column(Float, nullable=True)
    frame_count = Column(Integer, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    status = Column(String(16), nullable=False, default="queued")  # VariationStatus
    rendered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
