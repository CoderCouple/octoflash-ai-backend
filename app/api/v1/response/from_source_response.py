from pydantic import BaseModel

from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse
from app.api.v1.response.project_response import ProjectResponse
from app.api.v1.response.scene_response import SceneResponse


class CreateProjectFromSourceResponse(BaseModel):
    """Response envelope for `POST /projects/from-source`.

    Returns the empty project shell + classification + the WorkflowExecution
    row tracking the analyze run. Frontend polls `GET /executions/{execution.id}`
    until `status == COMPLETED`, then re-fetches the project to see the
    populated brief.
    """

    project: ProjectResponse
    source_type: str  # "youtube_long" | "youtube_short" | "medium" | "substack"

    scenes: list[SceneResponse] = []
    execution: WorkflowExecutionResponse | None = None
