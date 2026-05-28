"""UserService — auto-provisioning + profile + context switching.

`get_or_create_user` is the entrypoint called from `get_user_context` on
every authenticated request. On first sign-in it provisions a Personal org,
an owner membership, a Default workspace, and a Stripe customer (no-op if
Stripe isn't configured). Subsequent calls just bump `last_login_at`.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.user_response import UserPreferences
from app.common.enum.org import MembershipStatus, OrgRole
from app.common.exceptions import EntityNotFoundError
from app.db.repository.org_membership_repository import OrgMembershipRepository
from app.db.repository.organization_repository import OrganizationRepository
from app.db.repository.user_preference_repository import UserPreferenceRepository
from app.db.repository.user_repository import UserRepository
from app.db.repository.workspace_repository import WorkspaceRepository
from app.model.org_membership_model import OrgMembership
from app.model.organization_model import Organization
from app.model.user_model import User
from app.model.workspace_model import Workspace
from app.service.billing_service import BillingService

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.membership_repo = OrgMembershipRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        self.preference_repo = UserPreferenceRepository(db)
        self.billing_service = BillingService(db)

    async def get_or_create_user(
        self, cognito_sub: str, email: str | None = None
    ) -> User:
        """Look up user by cognito_sub; auto-provision on first sign-in."""
        user = await self.user_repo.get_by_cognito_sub(cognito_sub)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            await self.user_repo.update(user)
            return user

        return await self._auto_provision(cognito_sub, email)

    async def _auto_provision(self, cognito_sub: str, email: str | None) -> User:
        """Create user + personal org + owner membership + default workspace."""
        logger.info(
            "Auto-provisioning user for sub=%s email=%s", cognito_sub, email
        )

        user = User(
            cognito_sub=cognito_sub,
            email=email,
            display_name=email.split("@")[0] if email else None,
            last_login_at=datetime.now(timezone.utc),
        )
        user = await self.user_repo.create(user)

        org = Organization(
            name="Personal",
            slug=_slugify(f"personal-{user.id[-8:]}"),
            plan="free",
            created_by=user.id,
            updated_by=user.id,
        )
        org = await self.org_repo.create(org)

        membership = OrgMembership(
            org_id=org.id,
            user_id=user.id,
            role=OrgRole.OWNER.value,
            status=MembershipStatus.ACTIVE.value,
        )
        await self.membership_repo.create(membership)

        workspace = Workspace(
            org_id=org.id,
            name="Default",
            slug="default",
            created_by=user.id,
            updated_by=user.id,
        )
        workspace = await self.workspace_repo.create(workspace)

        try:
            await self.billing_service.ensure_stripe_customer(org.id, org.name, email)
        except Exception:
            logger.warning("Stripe customer creation skipped for org=%s", org.id)

        user.default_org_id = org.id
        user.default_workspace_id = workspace.id
        await self.user_repo.update(user)

        logger.info(
            "Auto-provisioned user=%s org=%s workspace=%s",
            user.id,
            org.id,
            workspace.id,
        )
        return user

    async def get_user(self, user_id: str) -> User | None:
        return await self.user_repo.get_by_id(user_id)

    async def ensure_default_tenancy(self, user_id: str) -> User:
        """Make sure `user_id` has a default org + workspace + owner
        membership. Used by the dev fallback path on /me when no Cognito
        JWT is present — the canonical dev user (`settings.default_user_id`)
        exists in the DB but may not have been auto-provisioned a tenancy
        the way a Cognito-backed user is.

        Idempotent: returns the user as-is if it already has both
        `default_org_id` and `default_workspace_id`.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)
        if user.default_org_id and user.default_workspace_id:
            return user

        logger.info(
            "ensure_default_tenancy: bootstrapping org/workspace for user=%s", user.id,
        )
        org = Organization(
            name="Personal",
            slug=_slugify(f"personal-{user.id[-8:]}"),
            plan="free",
            created_by=user.id,
            updated_by=user.id,
        )
        org = await self.org_repo.create(org)

        membership = OrgMembership(
            org_id=org.id,
            user_id=user.id,
            role=OrgRole.OWNER.value,
            status=MembershipStatus.ACTIVE.value,
        )
        await self.membership_repo.create(membership)

        workspace = Workspace(
            org_id=org.id,
            name="Default",
            slug="default",
            created_by=user.id,
            updated_by=user.id,
        )
        workspace = await self.workspace_repo.create(workspace)

        user.default_org_id = org.id
        user.default_workspace_id = workspace.id
        user = await self.user_repo.update(user)
        return user

    async def update_profile(
        self,
        user_id: str,
        display_name: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)

        if display_name is not None:
            user.display_name = display_name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        user.updated_at = datetime.now(timezone.utc)
        return await self.user_repo.update(user)

    async def switch_context(
        self,
        user_id: str,
        org_id: str | None = None,
        workspace_id: str | None = None,
    ) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)

        if org_id is not None:
            user.default_org_id = org_id
        if workspace_id is not None:
            user.default_workspace_id = workspace_id
        user.updated_at = datetime.now(timezone.utc)
        return await self.user_repo.update(user)

    # ── Preferences ─────────────────────────────────────────────────

    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Return validated preferences (empty defaults if no row)."""
        raw = await self.preference_repo.get(user_id)
        return UserPreferences.model_validate(raw)

    async def update_preferences(
        self, user_id: str, partial: dict[str, Any]
    ) -> UserPreferences:
        """Sparse-merge `partial` into the user's prefs blob and return the
        full merged result. Validation runs through `UserPreferences` so a
        bad client payload 4xx'd at the controller before reaching here.
        """
        if not partial:
            return await self.get_preferences(user_id)
        merged = await self.preference_repo.merge(user_id, partial)
        return UserPreferences.model_validate(merged)
