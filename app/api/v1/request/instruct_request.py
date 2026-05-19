from pydantic import BaseModel, Field


class InstructSceneRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=2000)
    """Natural-language edit, e.g. "shift the title up", "add a chart at 2s"."""
