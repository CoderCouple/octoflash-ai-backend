"""
FastAPI application entry point for Octoflash AI Backend.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import router as api_router
from app.api.v1.controller.billing_webhook_api import router as stripe_webhook_router
from app.api.v1.controller.oauth_callback_api import router as oauth_callback_router
from app.common.exceptions import register_exception_handlers
from app.settings import settings

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# SQLAlchemy ships its own configured loggers — when DEBUG=true is set in
# the env, the propagation to the root logger duplicates every SQL line
# (once from sqlalchemy's default handler, once via basicConfig). Cap them
# at WARNING unconditionally; set DB_ECHO=true on the engine if you
# actually need wire-level query debugging.
for _name in (
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "sqlalchemy.orm",
):
    logging.getLogger(_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    _bootstrap_storage_buckets()

    yield

    logger.info("Shutting down application")


def _bootstrap_storage_buckets() -> None:
    """Make sure the Supabase `avatars` + `renders` buckets exist.

    Idempotent — if both already exist, supabase-py returns the existing
    list and we no-op. Skipped silently when SUPABASE_SERVICE_ROLE_KEY
    is unset (local dev / tests) so the app still boots without the
    storage backend wired.

    Failures are logged but never block startup — a transient Supabase
    outage shouldn't take the API down, and bucket creation is one-time
    work that can be retried on the next deploy.
    """
    if not settings.supabase_service_role_key:
        logger.info("storage bootstrap skipped (SUPABASE_SERVICE_ROLE_KEY unset)")
        return
    try:
        from app.service.supabase_storage_service import get_storage_service

        get_storage_service().ensure_buckets()
        logger.info("storage bootstrap ok (avatars + renders buckets verified)")
    except Exception:  # noqa: BLE001
        logger.exception("storage bootstrap failed — continuing without ensure")


app = FastAPI(
    title=settings.app_name,
    description=settings.app_desc,
    debug=settings.debug,
    version=settings.app_version,
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router)

# Serve uploaded avatars (and any other user-uploaded local assets) from
# `{settings.local_storage_path}` under /storage/*. In prod these should
# move to S3/CloudFront — wire `S3_PUBLIC_BASE_URL` and the upload
# endpoint will switch over.
_storage_root = Path(settings.local_storage_path or "storage").resolve()
(_storage_root / "avatars").mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(_storage_root)), name="storage")

# Stripe webhook is mounted at root (no /api/v1 prefix, no JWT auth — the
# signature header is the credential).
app.include_router(stripe_webhook_router)
# OAuth provider redirects land at /oauth/callback/{platform} — root-mounted
# because the bearer token isn't carried in the redirect. `state` (signed
# JWT) is the auth.
app.include_router(oauth_callback_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning application metadata."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "environment": settings.environment,
        "api_docs": "/docs",
    }
