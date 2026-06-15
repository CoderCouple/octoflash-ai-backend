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
    op.alter_column("user", "cognito_sub", new_column_name="auth_sub")
    # Rename the supporting index too so it stays self-describing.
    op.execute("ALTER INDEX IF EXISTS ix_user_cognito_sub RENAME TO ix_user_auth_sub")


def downgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS ix_user_auth_sub RENAME TO ix_user_cognito_sub")
    op.alter_column("user", "auth_sub", new_column_name="cognito_sub")
