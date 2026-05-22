from datetime import datetime

from pydantic import BaseModel


class CredentialResponse(BaseModel):
    """Vault entry as returned to the UI — never carries the raw value."""

    id: str
    name: str
    masked_value: str
    is_set: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
