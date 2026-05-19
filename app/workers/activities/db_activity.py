"""
DB write activities — job status updates and variation inserts.

Each opens its own short-lived async session (not the request-scoped one) so
Temporal can retry the activity on its own schedule without leaning on
FastAPI's lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

# Side-effect import: ensures every model is in Base.metadata so FK resolution
# works inside activity-owned sessions (which don't share the request lifecycle).
import app.model  # noqa: F401
from app.db.engine import get_async_engine
from app.db.repository.job_repository import JobRepository
from app.db.repository.variation_repository import VariationRepository
from app.model.variation_model import Variation


def _session_factory() -> async_sessionmaker[AsyncSession]:
    """Build a fresh session factory bound to the worker's engine.

    Not cached because the activity may be retried after the engine is
    disposed in some failure scenarios.
    """
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@dataclass
class UpdateJobInput:
    job_id: str
    status: str | None = None
    progress: int | None = None
    log_entry: dict[str, Any] | None = None
    output_url: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    workflow_id: str | None = None
    run_id: str | None = None


@activity.defn(name="update_job")
async def update_job_activity(payload: UpdateJobInput) -> None:
    """Patch the Job row. Called at workflow status transitions."""
    factory = _session_factory()
    async with factory() as session:
        repo = JobRepository(session)
        job = await repo.get_by_id(payload.job_id)
        if job is None:
            # Don't raise — the workflow shouldn't keep retrying a bad job id.
            activity.logger.warning("update_job: job %s not found", payload.job_id)
            return

        if payload.status is not None:
            job.status = payload.status
        if payload.progress is not None:
            job.progress = payload.progress
        if payload.output_url is not None:
            job.output_url = payload.output_url
        if payload.started_at is not None:
            job.started_at = payload.started_at
        if payload.finished_at is not None:
            job.finished_at = payload.finished_at
        if payload.workflow_id is not None:
            job.workflow_id = payload.workflow_id
        if payload.run_id is not None:
            job.run_id = payload.run_id
        if payload.log_entry is not None:
            # Postgres JSONB — copy + append so SQLAlchemy detects the change.
            logs = list(job.logs or [])
            logs.append(payload.log_entry)
            job.logs = logs

        await repo.update(job)
        await session.commit()


@dataclass
class InsertVariationInput:
    scene_id: str
    params_snapshot: dict[str, Any]
    video_url: str
    audio_url: str | None
    duration: float
    frame_count: int
    file_size: int
    status: str = "ready"


@activity.defn(name="insert_variation")
async def insert_variation_activity(payload: InsertVariationInput) -> str:
    """Insert a Variation row after a successful render. Returns the variation id."""
    factory = _session_factory()
    async with factory() as session:
        repo = VariationRepository(session)
        variation = Variation(
            scene_id=payload.scene_id,
            params_snapshot=payload.params_snapshot,
            video_url=payload.video_url,
            audio_url=payload.audio_url,
            duration=payload.duration,
            frame_count=payload.frame_count,
            file_size=payload.file_size,
            status=payload.status,
            rendered_at=datetime.utcnow(),
        )
        await repo.create(variation)
        await session.commit()
        return variation.id
