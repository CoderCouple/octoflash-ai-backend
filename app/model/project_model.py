import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, String, Text, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"prj_{uuid.uuid4()}"


class Project(Base):
    __tablename__ = "project"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    title = Column(String(255), nullable=False)
    source_url = Column(Text(), nullable=True)
    owner_id = Column(String(), nullable=True, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
