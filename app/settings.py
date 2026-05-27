import platform
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_env_file() -> str:
    """Pick which .env to load based on host:

      • macOS (your laptop)  →  .env.local
      • Linux (ECS task)     →  .env.dev

    On ECS the task definition's Environment + Secrets blocks still take
    precedence — pydantic-settings layers env vars over the file values,
    so the file is a baseline / fallback. Missing file is tolerated; reads
    fall through to the process environment.
    """
    return ".env.local" if platform.system() == "Darwin" else ".env.dev"


class Settings(BaseSettings):
    app_name: str = "Octoflash AI Backend"
    app_desc: str = "Scene-first Manim video editor API"
    app_version: str = "0.1.0"
    debug: bool = False
    # Opt-in SQL echo. DEBUG=true alone used to switch it on, which made
    # the worker log every SELECT/INSERT twice (sqlalchemy.engine + the
    # mirrored app logger) and drowned real activity output. Now it's
    # explicit — set DB_ECHO=true only when you actually want the wire
    # log for a specific query bug.
    db_echo: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8008

    # Database
    database_url: str | None = None
    postgres_user: str = "octoflash"
    postgres_password: str = "octoflash"
    postgres_db: str = "octoflash_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    db_ssl_require: bool = False

    # API
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = [
        "http://localhost:5173",  # Vite dev (frontend packages/web — default port)
        "http://localhost:5174",  # Vite dev (fallback when 5173 is taken)
        "http://localhost:3000",  # Next.js dev (pre-migration)
        "http://localhost:8008",  # backend itself (Swagger UI ↔ API)
    ]

    # Temporal — durable workflow runner. Two ways to configure the client:
    #
    # 1. Profile-based (preferred for local dev — keeps secrets out of .env.dev):
    #      Install Temporal CLI, then:
    #        temporal --profile cloud config set --prop address   --value '...tmprl.cloud:7233'
    #        temporal --profile cloud config set --prop namespace --value '<namespace>'
    #        temporal --profile cloud config set --prop api_key   --value '<paste here, not in chat>'
    #      Run worker with:  TEMPORAL_PROFILE=cloud make worker
    #      Profiles live in ~/Library/Application Support/temporalio/temporal.toml on macOS.
    #
    # 2. Env-var fallback (used when TEMPORAL_PROFILE is unset — e.g. in Docker / CI):
    #      TEMPORAL_ADDRESS=localhost:7233  (or '<ns>.<account>.tmprl.cloud:7233' for Cloud)
    #      TEMPORAL_NAMESPACE=default
    #      TEMPORAL_API_KEY=<empty for local; set for Cloud → auto-enables TLS>
    #
    # Same workflows + activities run in both modes — only the client changes.
    temporal_profile: str = ""  # if set, app/workers/client.py loads from temporal.toml
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_api_key: str = ""
    temporal_task_queue: str = "octoflash-renders"
    temporal_workflow_id_prefix: str = "octoflash"

    # Default user id services attribute new rows to until auth is wired into
    # the request layer. Mirrors the seed row in sql/schema/0001_octoflash_schema.sql.
    default_user_id: str = "user_00000000-0000-0000-0000-000000000001"

    # AWS Cognito — JWT verification only. Signup/login/MFA all happen in the
    # Hosted UI; the backend just validates the resulting Bearer token.
    cognito_user_pool_id: str = ""
    cognito_region: str = "us-west-2"
    cognito_app_client_id: str = ""

    # Stripe — billing. All Stripe interactions are no-ops while
    # `stripe_secret_key` is empty (dev / test stays uncoupled). Webhook
    # signing secret is required for any real Stripe event delivery.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_pro: str = ""
    stripe_price_id_enterprise: str = ""

    # Playground — user-supplied ManimGL code (the /playground page on the FE).
    #
    # Two modes, picked by `playground_sandbox_mode`:
    #
    #   "docker"  (default, PRODUCTION) — run inside a hardened container
    #             built via `make playground-image`. Isolation: network=none,
    #             non-root, capped RAM/CPU, only the per-render dir mounted
    #             RW, host wall-clock timeout. If Docker isn't reachable the
    #             endpoint returns 503 — never silently falls back.
    #
    #   "local"   (DEV ONLY) — invoke `manimgl` directly on the host. No
    #             isolation. Submitted code runs with the server's user and
    #             full network access. Useful for laptop iteration when you
    #             trust everyone who can reach the API.
    #
    # Never set `playground_sandbox_mode=local` on a deployment exposed to
    # the public internet.
    playground_sandbox_mode: str = "docker"
    playground_docker_bin: str = "docker"
    # ManimGL (3Blue1Brown) — image built from infra/playground-runner/Dockerfile
    # via `make playground-image`. ManimGL is required because the /playground
    # frontend presets use `from manimlib import *`.
    playground_docker_image: str = "octoflash-playground-runner:latest"
    playground_local_bin: str = "manimgl"
    playground_timeout_seconds: int = 120
    playground_memory_limit: str = "1g"
    playground_cpu_limit: str = "1.0"
    playground_pids_limit: int = 128

    @property
    def temporal_is_cloud(self) -> bool:
        return bool(self.temporal_api_key)

    @property
    def cognito_jwks_url(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com/"
            f"{self.cognito_user_pool_id}/.well-known/jwks.json"
        )

    @property
    def cognito_issuer(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com/"
            f"{self.cognito_user_pool_id}"
        )

    # Anthropic (script generator + describer + evaluator)
    anthropic_api_key: str = ""
    planner_model: str = "claude-sonnet-4-5"
    # The script generator uses Opus for long structured Manim code generation.
    script_model: str = "claude-opus-4-7"

    # ElevenLabs (voiceover via manim-voiceover inside the Manim subprocess)
    eleven_api_key: str = ""

    # Local storage root for source videos, extracted frames, generated scripts,
    # render outputs, voiceover MP3 cache, etc. Mirrored S3 keys live under
    # the same relative tree.
    local_storage_path: str = "./storage"

    # AWS / S3
    aws_region: str = "us-west-2"
    s3_bucket_renders: str = "octoflash-renders-dev"
    s3_bucket_exports: str = "octoflash-exports-dev"
    s3_public_base_url: str = ""

    # Whisper
    whisper_model: str = "large-v3"

    # YouTube ingestion (channels feature)
    # If `youtube_api_key` is set, YouTubeFetcherService uses the official Data
    # API v3 (reliable, has quota). Otherwise it falls back to yt-dlp (no key,
    # no quota, more brittle). Channel video sync defaults to fetching the
    # most recent N videos per call.
    youtube_api_key: str = ""
    channel_sync_max_videos: int = 50

    # Manim
    manim_quality_preview: str = "low_quality"
    manim_quality_export: str = "high_quality"
    manim_output_dir: str = "./media"

    # Credential vault encryption key (Fernet, base64-encoded 32 bytes). When
    # empty (dev default) values are stored plaintext — a startup warning is
    # logged. Generate with: `python -c "from cryptography.fernet import
    # Fernet; print(Fernet.generate_key().decode())"`.
    credential_encryption_key: str = ""

    # ── OAuth — publishing targets ──────────────────────────────────────────
    # Each platform's Authorization Code (sometimes + PKCE) flow needs a
    # client_id + client_secret + redirect_uri triple from that platform's
    # developer console. Per-platform naming (rather than a single
    # GOOGLE_OAUTH_* prefix) so each platform's keys live under one
    # consistent prefix in the .env file.
    #
    # Empty client_id makes the corresponding `Connect <platform>` endpoint
    # return 501 rather than crash — a half-configured deployment fails
    # loudly per platform instead of globally.
    #
    # `<platform>_redirect_uri` MUST match what's registered in the
    # platform's developer console exactly (scheme + host + path).
    #
    # On a successful connect the backend redirects the browser back to:
    #   {frontend_url}/targets?connected=<target_id>
    frontend_url: str = "http://localhost:5173"
    # State token signing key — independent of credential_encryption_key so
    # rotating one doesn't invalidate the other. Falls back to credential key
    # in dev, but production should set a dedicated secret (32-byte base64).
    oauth_state_secret: str = ""

    # YouTube — Google OAuth 2.0. Configure at
    # https://console.cloud.google.com/apis/credentials
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_redirect_uri: str = "http://localhost:8008/oauth/youtube/callback"

    # TikTok for Developers (Login Kit + Content Posting API).
    # TikTok calls the public id "client key" rather than "client id".
    # Configure at https://developers.tiktok.com/apps/
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = "http://localhost:8008/oauth/tiktok/callback"

    # Instagram — Facebook Login for Business + Instagram Graph API. Meta
    # calls them "app_id / app_secret" rather than "client_id / client_secret".
    # `ig_business_account_id` is the linked-Page's IG Business Account id —
    # static config per deploy since IG publishing requires it on every call.
    # Configure under Meta for Developers (App → Use cases → Instagram).
    ig_app_id: str = ""
    ig_app_secret: str = ""
    ig_redirect_uri: str = "http://localhost:8008/oauth/instagram/callback"
    ig_business_account_id: str = ""

    # LinkedIn — Marketing Developer Platform.
    # Configure at https://www.linkedin.com/developers/apps
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8008/oauth/linkedin/callback"

    # X (Twitter) — OAuth 2.0 with PKCE (required).
    # Configure at https://developer.x.com/en/portal/dashboard
    x_client_id: str = ""
    x_client_secret: str = ""
    x_redirect_uri: str = "http://localhost:8008/oauth/x/callback"

    model_config = SettingsConfigDict(
        env_file=_detect_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def _quoted_password(self) -> str:
        """URL-encode the password so special chars don't break URL parsing."""
        return quote(self.postgres_password, safe="")

    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self._quoted_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def asyncpg_dsn(self) -> str:
        """Direct asyncpg DSN (no SQLAlchemy prefix) for bulk work / workers."""
        if self.database_url:
            url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            url = (
                f"postgresql://{self.postgres_user}:{self._quoted_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        if self.db_ssl_require:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
        return url

    @property
    def sync_database_url(self) -> str:
        if self.database_url:
            url = self.database_url.replace("postgresql://", "postgresql+psycopg://")
        else:
            url = (
                f"postgresql+psycopg://{self.postgres_user}:{self._quoted_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        if self.db_ssl_require:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
        return url


settings = Settings()
