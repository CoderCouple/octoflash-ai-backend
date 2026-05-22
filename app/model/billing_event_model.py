"""BillingEvent — append-only audit log of every processed Stripe webhook.

Used for two things: (1) idempotency — we skip events we've already seen by
`stripe_event_id`; (2) post-hoc debugging — the full `payload` is kept so
we can replay or inspect what Stripe sent.
"""

import uuid

from sqlalchemy import TIMESTAMP, Column, String, Text, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"be_{uuid.uuid4()}"


class BillingEvent(Base):
    __tablename__ = "billing_event"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    stripe_event_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False)
    org_id = Column(String(), nullable=True, index=True)
    payload = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
