import platform
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_env_file() -> str:
    """Load .env.local on macOS (dev laptop), .env.dev on Linux (cloud)."""
    return ".env.local" if platform.system() == "Darwin" else ".env.dev"


class Settings(BaseSettings):
    app_name: str = "Octoflash AI Backend"
    app_desc: str = "Scene-first Manim video editor API"
    app_version: str = "0.1.0"
    debug: bool = False
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
        "http://localhost:5173",  # Vite dev (frontend packages/web)
        "http://localhost:3000",  # Next.js dev (pre-migration)
    ]

    # Temporal — durable workflow runner. Two ways to configure the client:
    #
    # 1. Profile-based (preferred for local dev — keeps secrets out of .env):
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

    @property
    def temporal_is_cloud(self) -> bool:
        return bool(self.temporal_api_key)

    # Anthropic (planner LLM)
    anthropic_api_key: str = ""
    planner_model: str = "claude-sonnet-4-5"

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
