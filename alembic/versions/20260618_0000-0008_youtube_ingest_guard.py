"""youtube_ingest_guard table.

Revision ID: 0008_youtube_ingest_guard
Revises: 0007_scene_render
Create Date: 2026-06-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_youtube_ingest_guard"
down_revision: str | None = "0007_scene_render"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "youtube_ingest_guard",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("blocked_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "key", name="uq_youtube_ingest_guard_scope_key"),
    )
    op.create_index(op.f("ix_youtube_ingest_guard_scope"), "youtube_ingest_guard", ["scope"])
    op.create_index(op.f("ix_youtube_ingest_guard_key"), "youtube_ingest_guard", ["key"])
    op.create_index(
        op.f("ix_youtube_ingest_guard_blocked_until"),
        "youtube_ingest_guard",
        ["blocked_until"],
    )

    # Match the deny-all RLS posture of every other table in the schema
    # (see 0006_rls_deny_all_public). Without this, Supabase PostgREST
    # via the publishable/anon key would expose every row. The BE
    # connects as `postgres` and bypasses RLS, so this only locks out
    # untrusted clients.
    op.execute(
        """
        ALTER TABLE youtube_ingest_guard ENABLE ROW LEVEL SECURITY;
        CREATE POLICY youtube_ingest_guard_deny_all ON youtube_ingest_guard
            AS PERMISSIVE FOR ALL TO public
            USING (false) WITH CHECK (false);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS youtube_ingest_guard_deny_all ON youtube_ingest_guard")
    op.drop_index(op.f("ix_youtube_ingest_guard_blocked_until"), table_name="youtube_ingest_guard")
    op.drop_index(op.f("ix_youtube_ingest_guard_key"), table_name="youtube_ingest_guard")
    op.drop_index(op.f("ix_youtube_ingest_guard_scope"), table_name="youtube_ingest_guard")
    op.drop_table("youtube_ingest_guard")
