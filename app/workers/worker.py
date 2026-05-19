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
logger = logging.getLogger("app.workers")


async def run() -> None:
    client = await connect_temporal()
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=ALL_WORKFLOWS,
        activities=ALL_ACTIVITIES,
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
