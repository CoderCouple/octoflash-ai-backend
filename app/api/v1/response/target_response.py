"""Target (publishing destination) response models.

`credential.value` is intentionally never returned — secrets only ever land
on the wire encrypted, and even then the FE has no use for them. The
response carries `has_credential: bool` so the UI can show a "connected"
indicator without exposing the blob.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.enum.target import TargetPlatform, TargetStatus


class TargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    platform: TargetPlatform
    external_id: str | None = None
    handle: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    status: TargetStatus
    credential_id: str | None = None
    has_credential: bool = Field(
        default=False,
        description="True when credential_id is set — the FE uses this to show "
                    "a 'connected' state without ever seeing the OAuth blob.",
    )
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    last_synced_at: datetime | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
