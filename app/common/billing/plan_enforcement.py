"""Plan-limit enforcement.

Each `check_*` method counts the current resource usage for the org and
raises `PlanLimitExceededError` (HTTP 402) when the org's plan limit would
be exceeded.

Enforcement is **disabled** when `settings.stripe_secret_key` is empty, so
dev / test environments without Stripe stay limit-free. Production deploys
that turn on Stripe automatically pick up enforcement.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.billing.plan_limits import get_plan_limits
from app.common.exceptions import PlanLimitExceededError
from app.model.org_membership_model import OrgMembership
from app.model.project_model import Project
from app.model.workspace_model import Workspace
from app.settings import settings


class PlanEnforcer:
    def __init__(self, db: AsyncSession):
        self.db = db

    @property
    def _enabled(self) -> bool:
        return bool(settings.stripe_secret_key)

    async def _count(self, model, *conds) -> int:
        q = select(func.count(model.id)).where(*conds)
        if hasattr(model, "is_deleted"):
            q = q.where(model.is_deleted == False)  # noqa: E712
        r = await self.db.execute(q)
        return r.scalar() or 0

    async def check_org_members(self, plan: str, org_id: str) -> None:
        if not self._enabled:
            return
        limits = get_plan_limits(plan)
        q = await self.db.execute(
            select(func.count(OrgMembership.id)).where(
                OrgMembership.org_id == org_id,
                OrgMembership.status.in_(["active", "invited"]),
            )
        )
        current = q.scalar() or 0
        if current >= limits.org_members:
            raise PlanLimitExceededError(
                "team members", current, limits.org_members, plan
            )

    async def check_workspaces(self, plan: str, org_id: str) -> None:
        if not self._enabled:
            return
        limits = get_plan_limits(plan)
        current = await self._count(Workspace, Workspace.org_id == org_id)
        if current >= limits.workspaces:
            raise PlanLimitExceededError(
                "workspaces", current, limits.workspaces, plan
            )

    async def check_projects(self, plan: str, org_id: str) -> None:
        if not self._enabled:
            return
        limits = get_plan_limits(plan)
        current = await self._count(Project, Project.org_id == org_id)
        if current >= limits.projects:
            raise PlanLimitExceededError(
                "projects", current, limits.projects, plan
            )
