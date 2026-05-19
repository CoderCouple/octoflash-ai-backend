from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorkflowNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    kind: str
    x: float
    y: float
    w: float | None = None
    h: float | None = None
    label: str | None = None
    scene_id: str | None = None
    style_override: str | None = None
    branch_label: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    from_node_id: str
    to_node_id: str
    kind: str
    created_at: datetime


class WorkflowResponse(BaseModel):
    nodes: list[WorkflowNodeResponse] = []
    edges: list[WorkflowEdgeResponse] = []
