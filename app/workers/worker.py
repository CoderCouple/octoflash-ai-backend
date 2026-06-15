"""
Temporal worker entrypoint.

Run locally:        make worker            # uses TEMPORAL_TARGET=localhost:7233
Run against cloud:  set TEMPORAL_API_KEY in env, then make worker

The same workflows + activities run in both modes — only the client config
differs (see app/workers/client.py).
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

from app.settings import settings
from app.workers.activities import ALL_ACTIVITIES
from app.workers.client import connect_temporal
from app.workers.workflows import ALL_WORKFLOWS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Silence SQLAlchemy's chatty engine/pool/orm loggers — when DB_ECHO=true
# is set on the engine, those will still emit (the level cap below applies
# to the propagation through Python's root logger, not to the engine's
# echo mechanism itself).
for _name in (
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "sqlalchemy.orm",
):
    logging.getLogger(_name).setLevel(logging.WARNING)

logger = logging.getLogger("app.workers")


def _bootstrap_storage_buckets() -> None:
    """Mirror of the API's startup bootstrap — the worker uploads final
    renders, so it needs the `renders` bucket to exist before the first
    ffmpeg_concat activity fires. Silent skip when storage isn't
    configured; never blocks worker startup."""
    if not settings.supabase_service_role_key:
        logger.info("storage bootstrap skipped (SUPABASE_SERVICE_ROLE_KEY unset)")
        return
    try:
        from app.service.supabase_storage_service import get_storage_service

        get_storage_service().ensure_buckets()
        logger.info("storage bootstrap ok (avatars + renders buckets verified)")
    except Exception:  # noqa: BLE001
        logger.exception("storage bootstrap failed — continuing without ensure")


async def run() -> None:
    _bootstrap_storage_buckets()
    client = await connect_temporal()
    # Default 100 (Temporal's normal) so hosted Anthropic gets the
    # parallelism it can comfortably handle. Drop to 1 via env when
    # running local-only against single-GPU Ollama, which serializes
    # internally and would otherwise queue calls past LiteLLM's
    # httpx timeout.
    import os
    max_act = int(os.environ.get("WORKER_MAX_CONCURRENT_ACTIVITIES", "100"))
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=ALL_WORKFLOWS,
        activities=ALL_ACTIVITIES,
        max_concurrent_activities=max_act,
    )
    logger.info(
        "Worker started — polling task queue %r against %s (%s)",
        settings.temporal_task_queue,
        settings.temporal_address,
        "cloud" if settings.temporal_is_cloud else "local",
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run())
