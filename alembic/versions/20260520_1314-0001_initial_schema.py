"""initial schema (fresh baseline from sql/schema/0001_octoflash_schema.sql)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-20 13:14:00.000000

This migration is a hand-written baseline. It executes the canonical DDL in
`sql/schema/0001_octoflash_schema.sql` verbatim. Treat the SQL file as the
source of truth for the schema; future migrations layer on top of it via
normal alembic `op.*` calls.

The previous migration history was cleared as part of the rewrite — there is
no prior `down_revision`.
"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# alembic/versions/<this>.py → repo_root/sql/schema/<file>.sql
_SQL_FILE = (
    Path(__file__).resolve().parents[2] / "sql" / "schema" / "0001_octoflash_schema.sql"
)


def upgrade() -> None:
    sql = _SQL_FILE.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    # Drop in reverse-dependency order. CASCADE handles FK chains; the DROP TYPE
    # block runs only after every dependent table is gone.
    for stmt in _DOWNGRADE_STATEMENTS:
        op.execute(stmt)


_DOWNGRADE_STATEMENTS = [
    # Tables (children → parents)
    "DROP TABLE IF EXISTS execution_log CASCADE",
    "DROP TABLE IF EXISTS execution_phase CASCADE",
    "DROP TABLE IF EXISTS workflow_execution CASCADE",
    "DROP TABLE IF EXISTS workflow_edge_instance CASCADE",
    "DROP TABLE IF EXISTS workflow_node_instance CASCADE",
    "DROP TABLE IF EXISTS workflow_node_prop CASCADE",
    "DROP TABLE IF EXISTS workflow_node_type CASCADE",
    "DROP TABLE IF EXISTS workflow CASCADE",
    "DROP TABLE IF EXISTS scene CASCADE",
    "DROP TABLE IF EXISTS project CASCADE",
    "DROP TABLE IF EXISTS target CASCADE",
    "DROP TABLE IF EXISTS source_video CASCADE",
    "DROP TABLE IF EXISTS source CASCADE",
    "DROP TABLE IF EXISTS user_purchase CASCADE",
    "DROP TABLE IF EXISTS credential CASCADE",
    'DROP TABLE IF EXISTS "user" CASCADE',
    # Enums (no dependents now)
    "DROP TYPE IF EXISTS log_level_enum",
    "DROP TYPE IF EXISTS execution_phase_status_enum",
    "DROP TYPE IF EXISTS execution_status_enum",
    "DROP TYPE IF EXISTS execution_trigger_enum",
    "DROP TYPE IF EXISTS node_prop_type_enum",
    "DROP TYPE IF EXISTS node_prop_group_enum",
    "DROP TYPE IF EXISTS workflow_status_enum",
    "DROP TYPE IF EXISTS target_status_enum",
    "DROP TYPE IF EXISTS target_platform_enum",
    "DROP TYPE IF EXISTS source_video_kind_enum",
    "DROP TYPE IF EXISTS source_platform_enum",
    "DROP TYPE IF EXISTS render_method_enum",
    "DROP TYPE IF EXISTS quality_enum",
    "DROP TYPE IF EXISTS orientation_enum",
    "DROP TYPE IF EXISTS scene_status_enum",
    "DROP TYPE IF EXISTS project_status_enum",
    "DROP TYPE IF EXISTS user_role_enum",
]
