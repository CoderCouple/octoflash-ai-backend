"""
Workflow registry. The worker imports `ALL_WORKFLOWS` and registers them.

Workflows are deterministic orchestrators. They can't do IO — they call
activities (which can). All retries, timeouts, and durability come from
Temporal automatically.

Two workflows back the source → MP4 pipeline:
  - AnalyzeProjectWorkflow  → kicked off by `POST /projects/from-source`,
                               produces transcript/description/manim_prompt on the Project row.
  - GenerateVideoWorkflow   → kicked off by `POST /projects/{id}/generate`,
                               plans clips, fans out per-clip render, stitches final MP4.
"""

from app.workers.workflows.analyze_workflow import AnalyzeProjectWorkflow
from app.workers.workflows.generate_workflow import GenerateVideoWorkflow
from app.workers.workflows.publish_workflow import PublishTargetWorkflow
from app.workers.workflows.regenerate_workflow import RegenerateClipWorkflow

ALL_WORKFLOWS = [
    AnalyzeProjectWorkflow,
    GenerateVideoWorkflow,
    RegenerateClipWorkflow,
    PublishTargetWorkflow,
]
