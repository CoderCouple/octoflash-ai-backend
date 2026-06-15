"""Enable RLS with a deny-all policy on every public-schema table.

Supabase's auto-generated PostgREST API (`/rest/v1/<table>`) accepts
any valid project key — including the publishable/anon key the FE
ships to every browser. Without RLS, that means anyone who can scrape
our FE bundle can read every row.

We never use the Data API — the app's data path is FE → Railway BE →
Postgres direct connection as `postgres` (which bypasses RLS, so this
migration doesn't change anything for our app code).

Adding RLS + a `USING (false)` policy on each table:
  * silences Supabase's "Unrestricted" dashboard warnings
  * hard-blocks the publishable / anon key from reading anything
  * leaves `postgres` (BE) untouched
  * is reversible per-table if a future feature wants to expose a
    table to the Data API with a real policy

Idempotent — checks pg_class.relrowsecurity / pg_policies first so a
re-run is a no-op. The DO block walks every table in `public` except
alembic's own bookkeeping (its existence implies it's already
protected by virtue of being self-contained).

Revision ID: 0006_rls_deny_all_public
Revises: 0005_user_auth_sub
Create Date: 2026-06-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0006_rls_deny_all_public"
down_revision: Union[str, None] = "0005_user_auth_sub"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            t text;
            policy_name text;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename != 'alembic_version'
            LOOP
                -- Enable RLS if not already on.
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE n.nspname = 'public' AND c.relname = t
                      AND c.relrowsecurity
                ) THEN
                    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
                END IF;

                -- Add the deny-all policy if not already present.
                policy_name := t || '_deny_all';
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = t
                      AND policyname = policy_name
                ) THEN
                    EXECUTE format(
                        'CREATE POLICY %I ON public.%I AS PERMISSIVE FOR ALL TO public USING (false) WITH CHECK (false)',
                        policy_name, t
                    );
                END IF;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    """Drop every `<table>_deny_all` policy + disable RLS.

    Intentionally narrow — only touches the policies this migration
    created. Other policies (if any are added later) survive.
    """
    op.execute(
        """
        DO $$
        DECLARE
            t text;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_deny_all', t);
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t);
            END LOOP;
        END $$;
        """
    )
