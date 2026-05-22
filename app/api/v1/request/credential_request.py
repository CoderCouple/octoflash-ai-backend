from pydantic import BaseModel, Field


class UpsertCredentialRequest(BaseModel):
    value: str = Field(..., min_length=1, max_length=8192)
