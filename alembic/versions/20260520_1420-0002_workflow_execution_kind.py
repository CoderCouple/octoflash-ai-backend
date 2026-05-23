"""workflow_execution.kind — first-class semantic kind enum (no-op).

Revision ID: 0002_workflow_execution_kind
Revises: 0001_initial_schema
Create Date: 2026-05-20 14:20:00.000000

When first written, 0001 didn't yet include `workflow_kind_enum` or the
`workflow_execution.kind` column, so this revision created both. The
canonical schema `sql/schema/0001_octoflash_schema.sql` (which 0001 executes
verbatim) has since been rewritten to include them, making this migration
redundant and causing `CREATE TYPE workflow_kind_enum already exists` on
fresh deploys.

Kept as a no-op so existing dev / staging databases that already stamped
`0002_workflow_execution_kind` in `alembic_version` can still `upgrade head`
without an unknown-revision error.
"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0002_workflow_execution_kind"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
