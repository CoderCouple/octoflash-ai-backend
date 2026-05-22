"""user_preference: JSONB blob of per-user settings, 1:1 with user.

Revision ID: 0007_user_preference
Revises: 0006_project_tenancy_columns
Create Date: 2026-05-21 18:00:00.000000

Satellite table keyed by user_id (PK). New preferences land as new keys in
the JSONB blob — no DB migration for additions. Backfills an empty row for
every existing user so `/me` can use a regular INNER JOIN.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_user_preference"
down_revision: Union[str, None] = "0006_project_tenancy_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_preference (
            user_id     TEXT PRIMARY KEY REFERENCES "user"(id) ON DELETE CASCADE,
            prefs       JSONB        NOT NULL DEFAULT '{}'::jsonb,
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
    op.execute('INSERT INTO user_preference (user_id) SELECT id FROM "user"')


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_preference CASCADE")
