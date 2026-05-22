"""billing: drop user_purchase; add subscription + billing_event.

Revision ID: 0005_billing
Revises: 0004_cognito_and_tenancy
Create Date: 2026-05-21 14:00:00.000000

`user_purchase` was a per-user one-off charge log; billing is now per-org,
subscription-based, with Subscription 1:1 with Organization and BillingEvent
as the webhook audit trail.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_billing"
down_revision: Union[str, None] = "0004_cognito_and_tenancy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_purchase CASCADE")

    op.execute(
        """
        CREATE TABLE subscription (
            id                     TEXT PRIMARY KEY DEFAULT ('sub_' || gen_random_uuid()) NOT NULL,
            org_id                 TEXT          NOT NULL UNIQUE,
            stripe_customer_id     VARCHAR(255)  NOT NULL,
            stripe_subscription_id VARCHAR(255)  UNIQUE,
            plan                   VARCHAR(30)   NOT NULL DEFAULT 'free',
            status                 VARCHAR(30)   NOT NULL DEFAULT 'active',
            seat_count             INTEGER       NOT NULL DEFAULT 1,
            current_period_start   TIMESTAMPTZ,
            current_period_end     TIMESTAMPTZ,
            cancel_at_period_end   VARCHAR(5)    NOT NULL DEFAULT 'false',
            created_at             TIMESTAMPTZ   NOT NULL DEFAULT now(),
            updated_at             TIMESTAMPTZ   NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_subscription_org_id ON subscription(org_id)")
    op.execute(
        "CREATE INDEX ix_subscription_stripe_customer_id "
        "ON subscription(stripe_customer_id)"
    )
    op.execute(
        "CREATE INDEX ix_subscription_stripe_subscription_id "
        "ON subscription(stripe_subscription_id)"
    )

    op.execute(
        """
        CREATE TABLE billing_event (
            id               TEXT PRIMARY KEY DEFAULT ('be_' || gen_random_uuid()) NOT NULL,
            stripe_event_id  VARCHAR(255) NOT NULL UNIQUE,
            event_type       VARCHAR(100) NOT NULL,
            org_id           TEXT,
            payload          TEXT         NOT NULL,
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_billing_event_stripe_event_id "
        "ON billing_event(stripe_event_id)"
    )
    op.execute("CREATE INDEX ix_billing_event_org_id ON billing_event(org_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing_event CASCADE")
    op.execute("DROP TABLE IF EXISTS subscription CASCADE")
    # user_purchase is not recreated — it was deprecated by this migration.
