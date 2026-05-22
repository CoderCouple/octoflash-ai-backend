"""Target (publishing destination) request models.

OAuth blob lives on `credential.value` (TEXT). Two paths to populate it:
  - Pass `credential_value` inline (test/dev path).
  - Real OAuth callback flow → creates a credential row separately, then
    PATCH /targets/:id with `credential_id`.
"""

from pydantic import BaseModel, Field

from app.common.enum.target import TargetPlatform, TargetStatus


class CreateTargetRequest(BaseModel):
    platform: TargetPlatform
    handle: str | None = Field(default=None, max_length=128)
    external_id: str | None = Field(default=None, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = None
    credential_value: str | None = Field(
        default=None,
        description="OAuth blob (JSON-serialised). If set, a credential row is "
                    "created and linked. Otherwise the target starts without creds "
                    "and PATCH can attach one later.",
    )


class UpdateTargetRequest(BaseModel):
    handle: str | None = Field(default=None, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = None
    status: TargetStatus | None = None
    credential_id: str | None = None
    credential_value: str | None = Field(
        default=None,
        description="Rotates the OAuth blob on the existing credential row, "
                    "or creates one if none is attached yet.",
    )
