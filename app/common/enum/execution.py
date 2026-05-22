"""Execution-lineage enums — workflow runs, per-activity phases, log lines.

Bind to native PG ENUM types via SQLAlchemy `Enum(MyEnum, name='my_enum',
create_type=False, values_callable=lambda e: [v.value for v in e])`. The
`name=` must match the PG type declared in sql/schema/0001_octoflash_schema.sql.
"""

from enum import Enum


class WorkflowStatus(str, Enum):
    """Top-level workflow lifecycle — DRAFT in progress, PUBLISHED is locked."""

    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class WorkflowKind(str, Enum):
    """Semantic kind of a workflow_execution — what the run is *for*.

    This is the system-of-record for the FE-facing kind. `temporal_workflow_type`
    on the same row holds the implementation class name (e.g.
    `AnalyzeProjectWorkflow`); the two are intentionally separate so we can
    swap implementation classes without breaking FE contracts.
    """

    ANALYZE = "analyze"          # source URL → transcript + description + manim_prompt
    GENERATE = "generate"        # brief → plan + per-clip render + ffmpeg concat
    REGENERATE_CLIP = "regenerate_clip"  # single scene re-render + re-stitch
    EXPORT = "export"            # full-quality re-encode of an existing project
    PREVIEW = "preview"          # low-quality preview stitch
    TRANSCRIBE = "transcribe"    # whisper-only run


class ExecutionTrigger(str, Enum):
    """What kicked off a workflow_execution row."""

    MANUAL = "MANUAL"
    CRON = "CRON"
    API = "API"


class ExecutionStatus(str, Enum):
    """Mirrors Temporal's terminal workflow execution states + our PENDING."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    TERMINATED = "TERMINATED"
    TIMED_OUT = "TIMED_OUT"


class ExecutionPhaseStatus(str, Enum):
    """Per-activity lifecycle inside one workflow_execution."""

    CREATED = "CREATED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
