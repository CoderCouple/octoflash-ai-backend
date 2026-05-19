from pydantic import BaseModel, Field


class AddBranchRequest(BaseModel):
    """Fan out from a node into a new branch path."""

    from_node_id: str
    branch_label: str = Field(..., min_length=1, max_length=64)
    style_override: str | None = None  # optional style preset applied to all scenes on branch
