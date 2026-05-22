"""Workflow request models — mirror React Flow's `toObject()` shape so the
client can serialize the canvas state straight to the wire.

Save flow: `PUT /workflows/:id` with PutWorkflowRequest. Server persists
`definition` verbatim into JSONB and replaces the projection rows in
workflow_node_instance + workflow_edge_instance.
"""

from typing import Any

from pydantic import BaseModel, Field


class ReactFlowPosition(BaseModel):
    x: float
    y: float


class ReactFlowViewport(BaseModel):
    x: float = 0
    y: float = 0
    zoom: float = 1


class WorkflowNodeIn(BaseModel):
    """One node as React Flow serializes it."""

    id: str = Field(..., description="Client-generated id (wni_<uuid> convention).")
    type: str = Field(..., description="Machine key of a workflow_node_type row.")
    position: ReactFlowPosition
    data: dict[str, Any] = Field(default_factory=dict)
    width: float | None = None
    height: float | None = None
    label: str | None = None


class WorkflowEdgeIn(BaseModel):
    """One edge as React Flow serializes it."""

    id: str = Field(..., description="Client-generated id (we_<uuid> convention).")
    source: str = Field(..., description="Source node id (must appear in `nodes`).")
    target: str = Field(..., description="Target node id (must appear in `nodes`).")
    sourceHandle: str | None = None
    targetHandle: str | None = None
    label: str | None = None
    data: dict[str, Any] | None = None


class WorkflowDefinitionIn(BaseModel):
    nodes: list[WorkflowNodeIn] = Field(default_factory=list)
    edges: list[WorkflowEdgeIn] = Field(default_factory=list)
    viewport: ReactFlowViewport = Field(default_factory=ReactFlowViewport)


class PutWorkflowRequest(BaseModel):
    """Full canvas-replace payload — the React Flow JSON the editor produces."""

    definition: WorkflowDefinitionIn
    name: str | None = None
    description: str | None = None
