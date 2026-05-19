from pydantic import BaseModel

from app.api.v1.response.scene_response import SceneResponse


class PlanFromPromptResponse(BaseModel):
    """Result of POST /projects/{id}/plan.

    `scenes` are the rows persisted to the DB (already created — frontend
    can render them immediately). `reasoning` is the planner's short
    explanation of the structure, surfaced for the user.
    """

    scenes: list[SceneResponse]
    reasoning: str = ""
