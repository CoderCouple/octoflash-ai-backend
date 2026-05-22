"""
FastAPI application entry point for Octoflash AI Backend.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.api.v1.controller.billing_webhook_api import router as stripe_webhook_router
from app.common.exceptions import register_exception_handlers
from app.settings import settings

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    yield

    logger.info("Shutting down application")


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
# Stripe webhook is mounted at root (no /api/v1 prefix, no JWT auth — the
# signature header is the credential).
app.include_router(stripe_webhook_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning application metadata."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "environment": settings.environment,
        "api_docs": "/docs",
    }
