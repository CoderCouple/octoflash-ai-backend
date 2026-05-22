"""WorkspaceService — CRUD for workspaces inside an org.

A workspace is the per-request tenancy unit (X-Workspace-Id). Slugs are
unique within an org. Soft-deleted workspaces hide from list/get; resources
that point at them stay queryable by id only.
"""

import re
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.workspace_response import WorkspaceResponse
from app.common.billing.plan_enforcement import PlanEnforcer
from app.common.exceptions import DuplicateEntityError, EntityNotFoundError
from app.db.repository.organization_repository import OrganizationRepository
from app.db.repository.workspace_repository import WorkspaceRepository
from app.model.workspace_model import Workspace


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class WorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.workspace_repo = WorkspaceRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.enforcer = PlanEnforcer(db)

    async def create_workspace(
        self,
        org_id: str,
        name: str,
        description: str | None = None,
        slug: str | None = None,
        actor_id: str | None = None,
    ) -> WorkspaceResponse:
        org = await self.org_repo.get_by_id(org_id)
        plan = org.plan if org else "free"
        await self.enforcer.check_workspaces(plan, org_id)

        final_slug = slug or _slugify(name)
        existing = await self.workspace_repo.get_by_org_and_slug(org_id, final_slug)
        if existing:
            raise DuplicateEntityError("Workspace", "slug", final_slug)

        workspace = Workspace(
            org_id=org_id,
            name=name,
            slug=final_slug,
            description=description,
            created_by=actor_id,
            updated_by=actor_id,
        )
        workspace = await self.workspace_repo.create(workspace)
        return WorkspaceResponse.model_validate(workspace)

    async def get_workspace(self, workspace_id: str) -> WorkspaceResponse:
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise EntityNotFoundError("Workspace", workspace_id)
        return WorkspaceResponse.model_validate(workspace)

    async def list_workspaces(
        self, org_id: str, offset: int = 0, limit: int = 20
    ) -> tuple[list[WorkspaceResponse], int]:
        workspaces, total = await self.workspace_repo.list_by_org(org_id, offset, limit)
        return [WorkspaceResponse.model_validate(w) for w in workspaces], total

    async def update_workspace(
        self,
        workspace_id: str,
        name: str | None = None,
        description: str | None = None,
        actor_id: str | None = None,
    ) -> WorkspaceResponse:
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise EntityNotFoundError("Workspace", workspace_id)

        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description
        workspace.updated_by = actor_id
        workspace.updated_at = datetime.now(timezone.utc)
        workspace = await self.workspace_repo.update(workspace)
        return WorkspaceResponse.model_validate(workspace)

    async def delete_workspace(
        self, workspace_id: str, actor_id: str | None = None
    ) -> None:
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise EntityNotFoundError("Workspace", workspace_id)
        await self.workspace_repo.soft_delete(workspace, actor_id)
