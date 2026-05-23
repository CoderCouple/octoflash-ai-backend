"""target_platform_enum: add 'linkedin' + 'x'.

Revision ID: 0003_target_platforms
Revises: 0002_execution_node
Create Date: 2026-05-23 01:00:00.000000

PG 12+ allows ALTER TYPE … ADD VALUE inside a transaction (the new value
just isn't usable until commit). Our prod RDS is PG 17, so the standard
op.execute(…) pattern works. `IF NOT EXISTS` makes this a no-op against
DBs created from the updated canonical SQL baseline (already includes
both values).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_target_platforms"
down_revision: Union[str, None] = "0002_execution_node"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE target_platform_enum ADD VALUE IF NOT EXISTS 'linkedin'")
    op.execute("ALTER TYPE target_platform_enum ADD VALUE IF NOT EXISTS 'x'")


def downgrade() -> None:
    # PG has no DROP VALUE for enum types — to remove you'd rename the type,
    # create a new one, migrate rows, drop the old. Left as a no-op since
    # these values are additive and harmless.
    pass
