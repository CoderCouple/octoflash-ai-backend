"""UserPreference — JSONB blob of per-user settings, 1:1 with User.

Schema-flexible by design: new preferences are added by extending the
`UserPreferences` Pydantic model in `app/api/v1/response/user_response.py`
— no DB migration needed for additions. `user_id` is the primary key
(strict 1:1; no separate row id) and ON DELETE CASCADE follows the user.

Pydantic is the source of truth for the shape; the DB just stores the raw
JSONB blob.
"""

from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class UserPreference(Base):
    __tablename__ = "user_preference"

    user_id = Column(
        String(),
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    prefs = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=func.now()
    )
