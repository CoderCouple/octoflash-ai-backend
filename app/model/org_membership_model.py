"""OrgMembership — (user, org, role) join.

`user_id` may be NULL for invitations sent to an email that hasn't signed up
yet; once that user signs in via Cognito, auto-provisioning attaches them by
matching `invited_email`.
"""

import uuid

from sqlalchemy import TIMESTAMP, Column, String, UniqueConstraint, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"om_{uuid.uuid4()}"


class OrgMembership(Base):
    __tablename__ = "org_membership"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_membership_org_user"),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    org_id = Column(String(), nullable=False, index=True)
    user_id = Column(String(), nullable=True, index=True)
    role = Column(String(30), nullable=False, default="member")
    status = Column(String(30), nullable=False, default="active")
    invited_by = Column(String(), nullable=True)
    invited_email = Column(String(320), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
