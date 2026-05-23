"""workflow_execution: add node_instance_id (nullable, FK, indexed).

Revision ID: 0002_execution_node
Revises: 0001_initial_schema
Create Date: 2026-05-23 00:00:00.000000

When an execution is started by clicking "Run" on a specific DAG node
(the new POST /workflows/{id}/nodes/{id}/run), this column points at that
node so the FE can render per-node run history with a plain SQL WHERE.
NULL for executions started by project-level routes
(POST /projects/from-source, POST /projects/{id}/generate).

Uses IF NOT EXISTS so it's a no-op on DBs created from the canonical SQL
baseline (which already includes the column).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_execution_node"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE workflow_execution "
        "ADD COLUMN IF NOT EXISTS node_instance_id TEXT "
        "REFERENCES workflow_node_instance(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_workflow_execution_node_instance_id "
        "ON workflow_execution(node_instance_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_workflow_execution_node_instance_id")
    op.execute("ALTER TABLE workflow_execution DROP COLUMN IF EXISTS node_instance_id")
