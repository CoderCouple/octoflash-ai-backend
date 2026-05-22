"""workflow_execution.kind — first-class semantic kind enum.

Revision ID: 0002_workflow_execution_kind
Revises: 0001_initial_schema
Create Date: 2026-05-20 14:20:00.000000

The baseline used `temporal_workflow_type` (the Python class name) as the only
hint of what a workflow execution was *for*. That leaked an implementation
detail into FE responses. This migration adds a proper typed `kind` enum
column on `workflow_execution`. New rows must set it; existing rows are
backfilled from `temporal_workflow_type`.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_workflow_execution_kind"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) New enum type.
    op.execute(
        """
        CREATE TYPE workflow_kind_enum AS ENUM (
          'analyze', 'generate', 'regenerate_clip', 'export', 'preview', 'transcribe'
        )
        """
    )

    # 2) Add column as NULLABLE first so the backfill can populate it.
    op.execute("ALTER TABLE workflow_execution ADD COLUMN kind workflow_kind_enum")

    # 3) Backfill from temporal_workflow_type. Unknown class names default to
    #    'analyze' — there are no live execution rows in dev yet, so the choice
    #    is mostly cosmetic; safer than failing.
    op.execute(
        """
        UPDATE workflow_execution SET kind = CASE
          WHEN temporal_workflow_type = 'AnalyzeProjectWorkflow'  THEN 'analyze'::workflow_kind_enum
          WHEN temporal_workflow_type = 'GenerateVideoWorkflow'   THEN 'generate'::workflow_kind_enum
          WHEN temporal_workflow_type = 'RegenerateClipWorkflow'  THEN 'regenerate_clip'::workflow_kind_enum
          ELSE 'analyze'::workflow_kind_enum
        END
        """
    )

    # 4) Tighten to NOT NULL.
    op.execute("ALTER TABLE workflow_execution ALTER COLUMN kind SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE workflow_execution DROP COLUMN IF EXISTS kind")
    op.execute("DROP TYPE IF EXISTS workflow_kind_enum")
