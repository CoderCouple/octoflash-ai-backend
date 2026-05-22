"""cognito + multi-tenancy (org, workspace, org_membership) + user reshape.

Revision ID: 0004_cognito_and_tenancy
Revises: 0003_dual_orientation
Create Date: 2026-05-21 13:00:00.000000

Reshapes `user` for Cognito-backed auth (drops password/role/phone/avatar/
email_verified/is_deleted; renames clerk_user_id→cognito_sub, name→display_name,
avatar→avatar_url; adds default_org_id, default_workspace_id, last_login_at).
Introduces `organization`, `org_membership`, `workspace` tables. Role moves
from User to OrgMembership; user_role_enum is dropped.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_cognito_and_tenancy"
down_revision: Union[str, None] = "0003_dual_orientation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- user table reshape ---------------------------------------------------
    op.execute('ALTER TABLE "user" RENAME COLUMN clerk_user_id TO cognito_sub')
    op.execute('ALTER TABLE "user" RENAME COLUMN name TO display_name')
    op.execute('ALTER TABLE "user" RENAME COLUMN avatar TO avatar_url')

    # Drop columns that no longer make sense (auth fields owned by Cognito;
    # role moves to org_membership).
    op.execute('ALTER TABLE "user" DROP COLUMN password')
    op.execute('ALTER TABLE "user" DROP COLUMN role')
    op.execute('ALTER TABLE "user" DROP COLUMN phone')
    op.execute('ALTER TABLE "user" DROP COLUMN email_verified')
    op.execute('ALTER TABLE "user" DROP COLUMN is_deleted')
    op.execute("DROP TYPE IF EXISTS user_role_enum")

    # Relax NOT NULL on fields Cognito may not provide on first sign-in.
    op.execute('ALTER TABLE "user" ALTER COLUMN email DROP NOT NULL')
    op.execute('ALTER TABLE "user" ALTER COLUMN display_name DROP NOT NULL')

    # New tenancy + lifecycle columns.
    op.execute('ALTER TABLE "user" ADD COLUMN default_org_id TEXT')
    op.execute('ALTER TABLE "user" ADD COLUMN default_workspace_id TEXT')
    op.execute('ALTER TABLE "user" ADD COLUMN last_login_at TIMESTAMPTZ')

    op.execute('CREATE INDEX IF NOT EXISTS ix_user_cognito_sub ON "user"(cognito_sub)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_user_email ON "user"(email)')

    # --- organization ---------------------------------------------------------
    op.execute(
        """
        CREATE TABLE organization (
            id          TEXT PRIMARY KEY DEFAULT ('org_' || gen_random_uuid()) NOT NULL,
            name        VARCHAR(255) NOT NULL,
            slug        VARCHAR(255) NOT NULL UNIQUE,
            plan        VARCHAR(30)  NOT NULL DEFAULT 'free',
            logo_url    VARCHAR(2048),
            is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
            created_by  TEXT,
            updated_by  TEXT,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_organization_slug ON organization(slug)")

    # --- org_membership -------------------------------------------------------
    op.execute(
        """
        CREATE TABLE org_membership (
            id            TEXT PRIMARY KEY DEFAULT ('om_' || gen_random_uuid()) NOT NULL,
            org_id        TEXT         NOT NULL,
            user_id       TEXT,
            role          VARCHAR(30)  NOT NULL DEFAULT 'member',
            status        VARCHAR(30)  NOT NULL DEFAULT 'active',
            invited_by    TEXT,
            invited_email VARCHAR(320),
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT uq_org_membership_org_user UNIQUE (org_id, user_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_org_membership_org_id ON org_membership(org_id)")
    op.execute("CREATE INDEX ix_org_membership_user_id ON org_membership(user_id)")

    # --- workspace ------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE workspace (
            id          TEXT PRIMARY KEY DEFAULT ('ws_' || gen_random_uuid()) NOT NULL,
            org_id      TEXT         NOT NULL,
            name        VARCHAR(255) NOT NULL,
            slug        VARCHAR(255) NOT NULL,
            description TEXT,
            is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
            created_by  TEXT,
            updated_by  TEXT,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT uq_workspace_org_slug UNIQUE (org_id, slug)
        )
        """
    )
    op.execute("CREATE INDEX ix_workspace_org_id ON workspace(org_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace CASCADE")
    op.execute("DROP TABLE IF EXISTS org_membership CASCADE")
    op.execute("DROP TABLE IF EXISTS organization CASCADE")

    # Reverse the user reshape. The dropped enum / columns are best-effort —
    # downgrade is here for completeness but not expected to be used in prod.
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS last_login_at')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS default_workspace_id')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS default_org_id')
    op.execute('DROP INDEX IF EXISTS ix_user_email')
    op.execute('DROP INDEX IF EXISTS ix_user_cognito_sub')
    op.execute('ALTER TABLE "user" ALTER COLUMN display_name SET NOT NULL')
    op.execute('ALTER TABLE "user" ALTER COLUMN email SET NOT NULL')

    op.execute(
        "CREATE TYPE user_role_enum AS ENUM ('USER', 'ADMIN', 'MEMBER')"
    )
    op.execute(
        'ALTER TABLE "user" ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE'
    )
    op.execute('ALTER TABLE "user" ADD COLUMN email_verified TIMESTAMPTZ')
    op.execute('ALTER TABLE "user" ADD COLUMN phone VARCHAR(64)')
    op.execute(
        "ALTER TABLE \"user\" ADD COLUMN role user_role_enum NOT NULL DEFAULT 'USER'"
    )
    op.execute(
        'ALTER TABLE "user" ADD COLUMN password VARCHAR(256) NOT NULL DEFAULT \'\''
    )

    op.execute('ALTER TABLE "user" RENAME COLUMN avatar_url TO avatar')
    op.execute('ALTER TABLE "user" RENAME COLUMN display_name TO name')
    op.execute('ALTER TABLE "user" RENAME COLUMN cognito_sub TO clerk_user_id')
