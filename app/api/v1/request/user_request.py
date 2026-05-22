from pydantic import BaseModel, ConfigDict, Field

from app.common.enum.scene import Orientation


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2048)


class SwitchContextRequest(BaseModel):
    organization_id: str | None = None
    workspace_id: str | None = None


class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=320)
    role: str = Field(default="member")


class UpdatePreferencesRequest(BaseModel):
    """Partial preferences update.

    Only keys *present* in the body are written; the rest are preserved.
    Explicit `null` clears a value. This mirrors the `UserPreferences`
    response shape — keep them in lockstep when adding new prefs.
    """

    model_config = ConfigDict(extra="forbid")

    default_orientation: Orientation | None = None
    default_voice_id: str | None = None
