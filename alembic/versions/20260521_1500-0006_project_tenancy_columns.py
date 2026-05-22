"""project: add org_id + workspace_id (nullable, indexed).

Revision ID: 0006_project_tenancy_columns
Revises: 0005_billing
Create Date: 2026-05-21 15:00:00.000000

Threads tenancy through the existing video-project rows. Both columns are
nullable for now so the legacy `default_user_id` fallback keeps working
while the request layer is migrated to require Cognito auth. Once every
write path passes ctx.organization_id + ctx.workspace_id, a follow-up can
tighten these to NOT NULL and add FKs.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_project_tenancy_columns"
down_revision: Union[str, None] = "0005_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE project ADD COLUMN org_id TEXT")
    op.execute("ALTER TABLE project ADD COLUMN workspace_id TEXT")
    op.execute("CREATE INDEX ix_project_org_id ON project(org_id)")
    op.execute("CREATE INDEX ix_project_workspace_id ON project(workspace_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_project_org_id")
    op.execute("ALTER TABLE project DROP COLUMN IF EXISTS workspace_id")
    op.execute("ALTER TABLE project DROP COLUMN IF EXISTS org_id")
