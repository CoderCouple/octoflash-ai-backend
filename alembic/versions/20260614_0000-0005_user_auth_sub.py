"""Rename user.cognito_sub → user.auth_sub.

Auth swapped from AWS Cognito to Supabase Auth — the column name is now
provider-neutral (auth.users.id from Supabase today, could be Google /
Auth0 / etc tomorrow). Existing rows are preserved as-is; the `sub`
value Supabase emits is the auth.users.id UUID, which for a freshly
linked account replaces the old Cognito-emitted sub string.

Revision ID: 0005_user_auth_sub
Revises: 0004_waitlist_entry
Create Date: 2026-06-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_user_auth_sub"
down_revision: Union[str, None] = "0004_waitlist_entry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent. Pre-rename dev DBs still have `cognito_sub`, but a fresh
    # install (e.g. brand-new Supabase project) runs the updated seed SQL
    # which already creates the column as `auth_sub`. Check the catalog so
    # this migration is a no-op in the second case.
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='user' AND column_name='cognito_sub'
          ) THEN
            ALTER TABLE "user" RENAME COLUMN cognito_sub TO auth_sub;
            ALTER INDEX IF EXISTS ix_user_cognito_sub RENAME TO ix_user_auth_sub;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='user' AND column_name='auth_sub'
          ) THEN
            ALTER INDEX IF EXISTS ix_user_auth_sub RENAME TO ix_user_cognito_sub;
            ALTER TABLE "user" RENAME COLUMN auth_sub TO cognito_sub;
          END IF;
        END $$;
        """
    )
