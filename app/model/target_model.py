"""Target — a publishing destination owned by the user.

(user_id, platform, external_id) is unique so the same YouTube channel can't
be added twice. `credential_id` (1:1) holds the OAuth blob via the credential
table — separation lets us encrypt creds centrally and keep target rows
secret-free.
"""

import uuid

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func

from app.common.enum.target import TargetPlatform, TargetStatus
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"tgt_{uuid.uuid4()}"


class Target(Base):
    __tablename__ = "target"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "external_id", name="uq_target_user_platform_external"
        ),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    user_id = Column(String(), ForeignKey("user.id"), nullable=False, index=True)
    platform = Column(
        SAEnum(
            TargetPlatform,
            name="target_platform_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        index=True,
    )
    external_id = Column(String(128), nullable=True)
    handle = Column(String(128), nullable=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(Text(), nullable=True)
    status = Column(
        SAEnum(
            TargetStatus,
            name="target_status_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
        default=TargetStatus.ACTIVE,
    )
    credential_id = Column(
        String(),
        ForeignKey("credential.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    connected_at = Column(TIMESTAMP(timezone=True), nullable=True)
    disconnected_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_synced_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
