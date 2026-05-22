"""scene.orientation column + per-orientation final URLs on project.

Revision ID: 0003_dual_orientation
Revises: 0002_workflow_execution_kind
Create Date: 2026-05-20 17:00:00.000000

Lets one project carry two parallel sets of clips — one rendered for
portrait, one for landscape — and produce two final MP4s in a single
generate call. The unique constraint on scene is widened to include
orientation so (project, n) can exist twice (once per orientation).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_dual_orientation"
down_revision: Union[str, None] = "0002_workflow_execution_kind"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE scene ADD COLUMN orientation orientation_enum NOT NULL DEFAULT 'portrait'"
    )
    op.execute("ALTER TABLE scene DROP CONSTRAINT uq_scene_project_n")
    op.execute(
        "ALTER TABLE scene ADD CONSTRAINT uq_scene_project_orientation_n "
        "UNIQUE (project_id, orientation, n)"
    )

    # Rename `final_video_url` → `final_portrait_video_url` and add the landscape twin.
    op.execute(
        "ALTER TABLE project RENAME COLUMN final_video_url TO final_portrait_video_url"
    )
    op.execute("ALTER TABLE project ADD COLUMN final_landscape_video_url TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE project DROP COLUMN IF EXISTS final_landscape_video_url")
    op.execute(
        "ALTER TABLE project RENAME COLUMN final_portrait_video_url TO final_video_url"
    )
    op.execute("ALTER TABLE scene DROP CONSTRAINT IF EXISTS uq_scene_project_orientation_n")
    op.execute(
        "ALTER TABLE scene ADD CONSTRAINT uq_scene_project_n UNIQUE (project_id, n)"
    )
    op.execute("ALTER TABLE scene DROP COLUMN IF EXISTS orientation")
