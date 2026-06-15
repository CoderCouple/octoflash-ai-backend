"""UserContext + RBAC dependencies.

`get_user_context` is the canonical auth dependency for protected routes:
JWT → User (auto-provisioned on first login) → Org membership check →
Workspace tenancy check → `UserContext`.

Active org / workspace can be overridden per-request via `X-Org-Id` and
`X-Workspace-Id` headers, falling back to the user's stored defaults.

`require_role(*roles)` is the RBAC gate factory used for owner/admin-only
endpoints (org settings, member management, billing writes).
"""

import logging
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth.supabase import get_current_user, get_current_user_optional
from app.db.session import get_db

logger = logging.getLogger(__name__)


class UserContext(BaseModel):
    actor_id: str  # Supabase auth.users.id (JWT `sub` claim)
    user_id: str  # Internal user_ id
    email: str | None = None
    organization_id: str  # Active org
    workspace_id: str  # Active workspace
    role: str  # Role in active org


async def get_actor_id(
    claims: dict[str, Any] | None = Depends(get_current_user_optional),
) -> str | None:
    """Return the auth `sub` from a valid JWT, or None if no token."""
    if claims is None:
        return None
    return claims.get("sub")


async def get_actor_id_required(
    claims: dict[str, Any] = Depends(get_current_user),
) -> str:
    """Like get_actor_id but raises 401 if no valid token."""
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )
    return sub  # type: ignore[no-any-return]


async def get_user_context(
    claims: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> UserContext:
    """Assemble a UserContext from JWT claims + DB lookups.

    Auto-provisions user / org / workspace / membership on first login.
    Resolves active org + workspace from headers or user defaults.
    """
    # Lazy imports — these modules are introduced in later phases; keeping the
    # imports deferred avoids circulars and lets this module load before they exist.
    from app.db.repository.org_membership_repository import OrgMembershipRepository
    from app.db.repository.workspace_repository import WorkspaceRepository
    from app.service.user_service import UserService

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )
    email = claims.get("email")

    user_service = UserService(db)
    user = await user_service.get_or_create_user(sub, email)

    # Resolve org
    org_id = x_org_id or user.default_org_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context. Set X-Org-Id header or default org.",
        )

    # Verify active membership
    membership_repo = OrgMembershipRepository(db)
    membership = await membership_repo.get(org_id, user.id)
    if not membership or membership.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    # Resolve workspace
    workspace_id = x_workspace_id or user.default_workspace_id
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workspace context. Set X-Workspace-Id header or default workspace.",
        )

    # Verify workspace belongs to org
    workspace_repo = WorkspaceRepository(db)
    workspace = await workspace_repo.get_by_id(workspace_id)
    if not workspace or workspace.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace does not belong to this organization",
        )

    return UserContext(
        actor_id=sub,
        user_id=user.id,
        email=email,
        organization_id=org_id,
        workspace_id=workspace_id,
        role=membership.role,
    )


async def get_user_context_or_default(
    claims: dict[str, Any] | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
) -> UserContext:
    """Like `get_user_context` but falls back to `settings.default_user_id`
    when no JWT is present. Used by /me routes so the FE can update the
    profile in local dev without a Supabase session — the user row
    already exists; we just need to bootstrap a default org / workspace
    on first request.

    Production behaviour is unchanged: when a JWT IS present we route
    through the canonical `get_user_context` flow (RBAC + tenancy
    enforced exactly the same way).
    """
    from app.service.user_service import UserService

    if claims is not None:
        # JWT present — delegate to the strict path.
        return await get_user_context(
            claims=claims, db=db, x_org_id=x_org_id, x_workspace_id=x_workspace_id,
        )

    # No JWT → dev fallback against the well-known default user.
    from app.settings import settings

    user_service = UserService(db)
    user = await user_service.ensure_default_tenancy(settings.default_user_id)

    org_id = x_org_id or user.default_org_id
    workspace_id = x_workspace_id or user.default_workspace_id
    if not org_id or not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user is missing org/workspace after bootstrap",
        )

    return UserContext(
        actor_id=user.auth_sub or user.id,
        user_id=user.id,
        email=user.email,
        organization_id=org_id,
        workspace_id=workspace_id,
        role="owner",  # dev fallback is always owner of its personal org
    )


def require_role(*roles: str):
    """Dependency factory enforcing role membership in the active org.

    Goes through `get_user_context_or_default` so that dev (no JWT)
    sessions are recognized as the default user with role=owner. In
    production with JWT present the canonical strict path runs
    underneath — full RBAC + tenancy enforcement is unchanged.
    """

    async def _check(ctx: UserContext = Depends(get_user_context_or_default)) -> UserContext:
        if ctx.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return ctx

    return _check
