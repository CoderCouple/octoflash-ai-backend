"""Workflow response models — the canonical canvas state plus normalised
projection rows.

`WorkflowResponse.definition` IS the React Flow tree (passed straight to
`<ReactFlow {...defn} />` on the client). `nodes` / `edges` are the
projection-table rows; FE doesn't need them for rebuild but they're handy
for ad-hoc UI like "list scene-type nodes".
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.common.enum.execution import WorkflowStatus


class WorkflowNodeInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    type_id: str
    scene_id: str | None = None
    x: float
    y: float
    w: float | None = None
    h: float | None = None
    label: str | None = None
    config: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowEdgeInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    source_instance_id: str
    target_instance_id: str
    source_handle: str | None = None
    target_handle: str | None = None
    label: str | None = None
    data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowResponse(BaseModel):
    """Full workflow record — `definition` is the source of truth for rebuild."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    user_id: str
    name: str | None = None
    description: str | None = None
    definition: dict[str, Any] | None = None
    execution_plan: dict[str, Any] | None = None
    status: WorkflowStatus

    cron: str | None = None
    last_run_at: datetime | None = None
    last_run_id: str | None = None
    last_run_status: str | None = None
    next_run_at: datetime | None = None

    nodes: list[WorkflowNodeInstanceResponse] = []
    edges: list[WorkflowEdgeInstanceResponse] = []

    created_at: datetime
    updated_at: datetime
