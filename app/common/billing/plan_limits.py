"""Plan-limit definitions per tier.

Values are placeholders for Octoflash — tune in Phase 8 once we have a feel
for free / pro / enterprise tradeoffs (renders per month, total minutes,
parallel workspaces, etc.). The structure mirrors Octopod's so enforcement
hooks can be wired in the meantime.
"""

from dataclasses import dataclass

from app.common.enum.org import OrgPlan


@dataclass(frozen=True)
class PlanLimits:
    workspaces: int
    projects: int
    org_members: int
    renders_per_month: int


FREE_LIMITS = PlanLimits(
    workspaces=1,
    projects=3,
    org_members=1,
    renders_per_month=20,
)

PRO_LIMITS = PlanLimits(
    workspaces=10,
    projects=100,
    org_members=10,
    renders_per_month=500,
)

ENTERPRISE_LIMITS = PlanLimits(
    workspaces=100,
    projects=10_000,
    org_members=100,
    renders_per_month=50_000,
)

_PLAN_MAP: dict[str, PlanLimits] = {
    OrgPlan.FREE.value: FREE_LIMITS,
    OrgPlan.PRO.value: PRO_LIMITS,
    OrgPlan.ENTERPRISE.value: ENTERPRISE_LIMITS,
}


def get_plan_limits(plan: str) -> PlanLimits:
    """Return limits for a plan tier. Defaults to free."""
    return _PLAN_MAP.get(plan, FREE_LIMITS)
