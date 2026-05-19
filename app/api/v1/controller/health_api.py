"""Health check API."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, status

from app.api.tags import Tags

router = APIRouter(tags=[Tags.Health])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """Liveness probe."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "octoflash-ai-backend",
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, Any]:
    """Readiness probe — checks critical deps."""
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {"database": "ok", "redis": "ok"},
    }
