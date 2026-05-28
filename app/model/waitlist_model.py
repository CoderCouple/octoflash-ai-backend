"""Waitlist / demo-request signups from the marketing site's contact form.

One row per email (UNIQUE). Re-submitting the same email is a no-op
from the DB's perspective — the controller returns a friendly
'already-on-list' message instead of erroring out.
"""

import uuid

from sqlalchemy import TIMESTAMP, Column, String, Text, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"wait_{uuid.uuid4()}"


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entry"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    email = Column(String(320), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=True)
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=True)
    # Where the signup came from — `contact`, `waitlist`, `demo-request`,
    # etc. Free-form so we don't need a migration to add a new entry-point.
    source = Column(String(40), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
