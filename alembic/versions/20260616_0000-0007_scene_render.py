"""scene_render table — per-clip render tracking + stderr stream sink.

Until now the FE only saw workflow-level phases (`planned` /
`clips_rendered` / `done`), so a 5–10 min Manim fan-out looked like a
single stall at `planned=COMPLETED`. This migration adds:

  * `scene_render` — one row per (scene, attempt). PENDING → RUNNING →
    SUCCEEDED | FAILED | TIMED_OUT. Records the chosen render_method
    (claude_codegen / strip_voiceover / fresh_no_voice / improved),
    started_at / completed_at / duration_ms, the output_ref the activity
    wrote to Supabase Storage, and (on failure) a sanitized error
    message. Temporal activity_id + attempt are recorded for cross-
    correlation with Temporal UI.

  * `execution_log.scene_render_id` (new, nullable) + relaxes the
    `execution_phase_id` NOT NULL constraint. A log line now belongs to
    EITHER a workflow phase OR a per-clip render — CHECK constraint
    enforces that exactly one of the two is set. This lets the Manim
    subprocess's stderr stream into execution_log scoped to its render.

  * RLS deny-all on the new table — matches migration 0006's pattern.

Revision ID: 0007_scene_render
Revises: 0006_rls_deny_all_public
Create Date: 2026-06-15 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_scene_render"
down_revision: Union[str, None] = "0006_rls_deny_all_public"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUS_VALUES = ("PENDING", "RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT")


def upgrade() -> None:
    # ── Enum types ───────────────────────────────────────────────────
    # Only the status enum is new. `render_method` reuses the existing
    # `render_method_enum` PG type from migration 0001 (values:
    # claude_voice / claude_voice_retry / claude_novoice /
    # claude_novoice_fresh / simple_fallback) — same set the Scene
    # model already maps via RenderMethod in app.common.enum.scene.
    sa.Enum(*_STATUS_VALUES, name="scene_render_status").create(
        op.get_bind(), checkfirst=True,
    )

    # ── scene_render ─────────────────────────────────────────────────
    op.create_table(
        "scene_render",
        sa.Column(
            "id",
            sa.Text(),
            primary_key=True,
            nullable=False,
            server_default=sa.text("'sr_' || gen_random_uuid()"),
        ),
        sa.Column(
            "scene_id",
            sa.Text(),
            sa.ForeignKey("scene.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_execution_id",
            sa.Text(),
            sa.ForeignKey("workflow_execution.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            postgresql.ENUM(*_STATUS_VALUES, name="scene_render_status", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "render_method",
            postgresql.ENUM(
                "claude_voice", "claude_voice_retry", "claude_novoice",
                "claude_novoice_fresh", "simple_fallback",
                name="render_method_enum", create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("output_ref", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("temporal_activity_id", sa.Text(), nullable=True),
        sa.Column("temporal_attempt", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_scene_render_scene", "scene_render", ["scene_id"])
    op.create_index("ix_scene_render_exec", "scene_render", ["workflow_execution_id"])

    # ── execution_log: polyvalent log target ─────────────────────────
    op.add_column(
        "execution_log",
        sa.Column(
            "scene_render_id",
            sa.Text(),
            sa.ForeignKey("scene_render.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.alter_column("execution_log", "execution_phase_id", nullable=True)
    op.create_check_constraint(
        "execution_log_target",
        "execution_log",
        "(execution_phase_id IS NOT NULL) OR (scene_render_id IS NOT NULL)",
    )
    op.create_index(
        "ix_execution_log_scene_render", "execution_log", ["scene_render_id"]
    )

    # ── RLS deny-all on scene_render (match migration 0006) ──────────
    op.execute(
        """
        ALTER TABLE scene_render ENABLE ROW LEVEL SECURITY;
        CREATE POLICY scene_render_deny_all ON scene_render
            AS PERMISSIVE FOR ALL TO public
            USING (false) WITH CHECK (false);
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS scene_render_deny_all ON scene_render"
    )
    op.execute("ALTER TABLE scene_render DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_execution_log_scene_render", table_name="execution_log")
    op.drop_constraint("execution_log_target", "execution_log", type_="check")
    op.alter_column("execution_log", "execution_phase_id", nullable=False)
    op.drop_column("execution_log", "scene_render_id")

    op.drop_index("ix_scene_render_exec", table_name="scene_render")
    op.drop_index("ix_scene_render_scene", table_name="scene_render")
    op.drop_table("scene_render")

    # Don't drop render_method_enum — it predates this migration.
    sa.Enum(name="scene_render_status").drop(op.get_bind(), checkfirst=True)
