"""
Workflow registry. The worker imports `ALL_WORKFLOWS` and registers them.

Workflows are deterministic orchestrators. They can't do IO — they call
activities (which can). All retries, timeouts, and durability come from
Temporal automatically.
"""

from app.workers.workflows.export_workflow import (
    ExportProjectWorkflow,
    PreviewProjectWorkflow,
)
from app.workers.workflows.transcribe_workflow import TranscribeSourceWorkflow
from app.workers.workflows.variation_workflow import (
    GenerateVariationsWorkflow,
    RerenderVariationWorkflow,
)

ALL_WORKFLOWS = [
    GenerateVariationsWorkflow,
    RerenderVariationWorkflow,
    PreviewProjectWorkflow,
    ExportProjectWorkflow,
    TranscribeSourceWorkflow,
]
