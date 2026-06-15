from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enum.scene import Orientation


class UserPreferences(BaseModel):
    """Per-user preferences. The Pydantic shape *is* the schema — adding a
    new preference is a single edit to this class. The DB stores the raw
    JSONB blob and applies no validation; this model is the only
    enforcement point.

    `extra="forbid"` means unknown keys 4xx loudly rather than silently
    drop. Bump this when there's a documented reason to be lenient (e.g.
    forward-compatible FE deployments).
    """

    model_config = ConfigDict(extra="forbid")

    default_orientation: Orientation | None = None
    default_voice_id: str | None = None
    # Add new preferences here.


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    auth_sub: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    default_org_id: str | None = None
    default_workspace_id: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # Populated by the controller from the user_preference satellite table.
    # Missing row → empty `UserPreferences` (all defaults).
    preferences: UserPreferences = UserPreferences()


class UserContextResponse(BaseModel):
    user: UserResponse
    organization_id: str
    workspace_id: str
    role: str
