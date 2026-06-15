"""User — Supabase-backed identity, auto-provisioned on first JWT.

Supabase Auth owns signup/signin/MFA/password-reset; this row is the
internal projection (one per `auth.users.id`) and the anchor every other
table points at. `default_org_id` + `default_workspace_id` are the
user's active tenancy when no `X-Org-Id` / `X-Workspace-Id` header is
sent. Role lives on OrgMembership, not here — users can hold different
roles in different orgs.
"""

import uuid

from sqlalchemy import TIMESTAMP, Column, String, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"user_{uuid.uuid4()}"


class User(Base):
    __tablename__ = "user"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    # JWT `sub` claim from the auth provider. Currently Supabase
    # auth.users.id (UUID). Name is provider-neutral so a future move
    # away from Supabase doesn't require a schema migration.
    auth_sub = Column(String(), unique=True, nullable=False, index=True)
    email = Column(String(320), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(2048), nullable=True)
    default_org_id = Column(String(), nullable=True)
    default_workspace_id = Column(String(), nullable=True)
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
