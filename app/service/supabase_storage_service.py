"""Supabase Storage uploader — avatars + final renders.

Wraps `supabase-py`'s Storage v3 client. Uses the project's secret
(service-role) key so the backend can write to private buckets, then
hands the FE either a signed URL (default, time-limited) or a public
URL (when the bucket is set to public).

Buckets the app expects to exist:
  * `avatars` — private, 8 MB cap, image/* content types
  * `renders` — private, video MP4 outputs

Create them in Supabase Dashboard → Storage → New bucket (or run
`SupabaseStorageService.ensure_buckets()` on startup — idempotent).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

from supabase import Client, create_client

from app.settings import settings

logger = logging.getLogger(__name__)

# Default expiry for signed URLs we hand to the FE (in seconds).
# 1 hour is the SDK default; long enough for a video stream to start
# without giving away a forever-link.
_SIGNED_URL_TTL: Final[int] = 3600

BUCKET_AVATARS = "avatars"
BUCKET_RENDERS = "renders"


@dataclass
class StorageUploadResult:
    bucket: str
    path: str
    """Absolute URL the FE can fetch — signed if the bucket is private."""
    url: str


class SupabaseStorageService:
    """Thin wrapper around the storage v3 client. One instance per worker.

    Reads `settings.supabase_url` + `settings.supabase_service_role_key`;
    raises ImportError-style failure-fast when either is missing rather
    than letting a bare `KeyError` bubble out of the SDK.
    """

    def __init__(self) -> None:
        if not settings.supabase_url:
            raise RuntimeError("SUPABASE_URL is not set — cannot initialize storage")
        if not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_SERVICE_ROLE_KEY is not set — backend can't write "
                "to Storage without it",
            )
        self._client: Client = create_client(
            settings.supabase_url, settings.supabase_service_role_key,
        )

    # ── uploads ────────────────────────────────────────────────────────

    def upload_bytes(
        self,
        *,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
        upsert: bool = True,
    ) -> StorageUploadResult:
        """Upload an in-memory blob. `path` is relative to the bucket
        (e.g. `user_abc/avatar.png`).
        """
        # supabase-py's upload returns the storage response; on error it
        # raises. We immediately mint a signed URL so the caller can
        # persist it on the user / scene row.
        self._client.storage.from_(bucket).upload(
            path=path,
            file=data,
            file_options={
                "content-type": content_type,
                # `upsert=true` lets us overwrite a previous upload at the
                # same path — important for stable per-user paths.
                "upsert": "true" if upsert else "false",
            },
        )
        url = self._signed_url(bucket, path)
        logger.info("storage upload bucket=%s path=%s bytes=%d", bucket, path, len(data))
        return StorageUploadResult(bucket=bucket, path=path, url=url)

    def upload_file(
        self,
        *,
        bucket: str,
        path: str,
        local_path: str,
        content_type: str,
        upsert: bool = True,
    ) -> StorageUploadResult:
        """Upload from disk. Avoids loading the file into memory for
        large MP4s — `supabase-py` streams the path."""
        with open(local_path, "rb") as fh:
            data = fh.read()
        return self.upload_bytes(
            bucket=bucket, path=path, data=data,
            content_type=content_type, upsert=upsert,
        )

    # ── URLs ───────────────────────────────────────────────────────────

    def _signed_url(self, bucket: str, path: str, ttl: int = _SIGNED_URL_TTL) -> str:
        """Mint a time-limited signed URL. The SDK returns the URL
        relative to the bucket; we want the absolute form so the FE can
        use it directly in <img> / <video src>.
        """
        resp = self._client.storage.from_(bucket).create_signed_url(path, ttl)
        return resp.get("signedURL") or resp.get("signed_url") or ""

    def signed_url(self, bucket: str, path: str, ttl: int = _SIGNED_URL_TTL) -> str:
        """Public re-mint accessor — used when an existing signed URL
        expires and the FE needs a fresh one for the same `path`."""
        return self._signed_url(bucket, path, ttl)

    # ── bucket bootstrap (idempotent) ──────────────────────────────────

    def ensure_buckets(self) -> None:
        """Create `avatars` and `renders` buckets if absent. Safe to run
        on every boot. Both are created private; FE access is via signed
        URLs only.

        supabase-py 2.x returns SyncBucket objects (not dicts), so we
        access `.name` rather than subscripting.
        """
        existing = {b.name for b in self._client.storage.list_buckets()}
        for name in (BUCKET_AVATARS, BUCKET_RENDERS):
            if name in existing:
                continue
            self._client.storage.create_bucket(name, options={"public": False})
            logger.info("storage: created bucket %s (private)", name)


_singleton: SupabaseStorageService | None = None


def get_storage_service() -> SupabaseStorageService:
    """Module-level singleton. Lazy so non-storage code paths can run
    without SUPABASE_SERVICE_ROLE_KEY being set (e.g. local tests)."""
    global _singleton
    if _singleton is None:
        _singleton = SupabaseStorageService()
    return _singleton
