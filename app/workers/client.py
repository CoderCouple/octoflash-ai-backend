"""
Temporal client factory — connects to either a local dev server or Temporal Cloud
using the same code. Mode is env-driven:

  Profile mode (preferred for local dev):
      Set TEMPORAL_PROFILE=<name> and define that profile via the Temporal CLI:
        temporal --profile <name> config set --prop address   --value '...'
        temporal --profile <name> config set --prop namespace --value '...'
        temporal --profile <name> config set --prop api_key   --value '...'
      Profiles are read from the SDK's standard TOML config (see locate_config_file).
      Keeps API keys off `.env.dev*` files.

  Env-var fallback:
      TEMPORAL_ADDRESS=localhost:7233 / <ns>.<account>.tmprl.cloud:7233
      TEMPORAL_NAMESPACE=default / <namespace>
      TEMPORAL_API_KEY=<empty for local; set for Cloud → enables TLS>

Both call paths land on `Client.connect(...)`. The rest of the system never
needs to know which mode is active.
"""

from __future__ import annotations

import logging
import os
import pathlib
import platform

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

from app.settings import settings

logger = logging.getLogger(__name__)


def locate_config_file() -> pathlib.Path:
    """Return the Temporal CLI's standard config-file path for the current OS."""
    home = pathlib.Path.home()
    system = platform.system()

    if system == "Darwin":
        return home / "Library/Application Support/temporalio/temporal.toml"
    if system == "Windows":
        app_data = os.getenv("AppData")
        if app_data is None:
            raise RuntimeError("AppData environment variable not set")
        return pathlib.Path(app_data) / "temporalio/temporal.toml"

    xdg = os.getenv("XDG_CONFIG_HOME")
    base = pathlib.Path(xdg) if xdg else (home / ".config")
    return base / "temporalio/temporal.toml"


async def connect_temporal() -> Client:
    """Build and return a Temporal `Client` from the active config source."""
    profile = settings.temporal_profile
    config_path = locate_config_file()

    if profile and config_path.is_file():
        logger.info(
            "Connecting to Temporal via profile %r (from %s)", profile, config_path
        )
        connect_config = ClientConfig.load_client_connect_config(
            profile=profile,
            config_file=str(config_path),
        )
        return await Client.connect(**connect_config)

    if profile and not config_path.is_file():
        logger.warning(
            "TEMPORAL_PROFILE=%r set but config file %s not found — "
            "falling back to TEMPORAL_ADDRESS env-var connect.",
            profile,
            config_path,
        )

    # Env-var fallback path (used in Docker / CI / when no profile is configured).
    if settings.temporal_is_cloud:
        logger.info(
            "Connecting to Temporal Cloud at %s (namespace=%s, env-var mode)",
            settings.temporal_address,
            settings.temporal_namespace,
        )
        return await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
            api_key=settings.temporal_api_key,
            tls=True,
        )

    logger.info(
        "Connecting to local Temporal at %s (namespace=%s)",
        settings.temporal_address,
        settings.temporal_namespace,
    )
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )


_cached_client: Client | None = None


async def get_temporal_client() -> Client:
    """Process-cached client. Safe to call repeatedly from request handlers."""
    global _cached_client
    if _cached_client is None:
        _cached_client = await connect_temporal()
    return _cached_client
