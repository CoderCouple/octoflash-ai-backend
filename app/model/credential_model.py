"""Credential — per-user secret. v1 use case: OAuth blob for targets (1:1).

`value` is TEXT to hold the full OAuth payload (access_token + refresh_token +
expires_at + scope, JSON-serialised). Generic enough for non-target secrets
later (API keys, webhook signing keys, etc.).
"""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, String, Text, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"cred_{uuid.uuid4()}"


class Credential(Base):
    __tablename__ = "credential"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    user_id = Column(String(), ForeignKey("user.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    value = Column(Text(), nullable=False)
    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
