"""Preview + export service — stub until the generate-video workflow lands in task 12.

The old preview/export workflows have been deleted along with the
template/variation machinery. The new pipeline is single-flow:
analyze → plan_clips → per-clip render → ffmpeg concat → final MP4. Once
that's in, preview/export become the same workflow with different quality
settings.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.response.workflow_execution_response import WorkflowExecutionResponse


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def queue_preview(
        self, project_id: str, end_node_id: str | None = None
    ) -> WorkflowExecutionResponse:
        raise NotImplementedError(
            "Preview pipeline not wired yet — pending task 12 (workflow rewire)."
        )

    async def queue_export(
        self, project_id: str, end_node_id: str | None = None, format: str = "mp4"
    ) -> WorkflowExecutionResponse:
        raise NotImplementedError(
            "Export pipeline not wired yet — pending task 12 (workflow rewire)."
        )
