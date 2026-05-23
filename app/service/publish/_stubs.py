"""TikTok / Instagram / LinkedIn / X publish stubs.

Each module shares the same `publish(*, video_path, metadata, token)` signature
expected by the registry. The protocols differ enough that a generic helper
isn't worth writing until two are wired:

  * **TikTok** — Content Posting API v2. Init / chunked PUT / status poll.
      https://developers.tiktok.com/doc/content-posting-api-reference-direct-post-video/

  * **Instagram** — Graph API container pattern (requires the video to be
    publicly reachable by URL, not a local file — needs S3 hosting first).
      https://developers.facebook.com/docs/instagram-platform/content-publishing/

  * **LinkedIn** — /v2/assets?action=registerUpload then ephemeral PUT then
    /v2/ugcPosts with the asset URN.
      https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/video-shares

  * **X** — v1.1 chunked media upload (INIT / APPEND / FINALIZE / STATUS) then
    v2 POST /tweets with the media id.
      https://developer.x.com/en/docs/x-api/v1/media/upload-media/api-reference/post-media-upload-init
"""

from __future__ import annotations

from pathlib import Path

from app.service.oauth_service import TokenBlob
from app.service.publish.models import PublishError, PublishMetadata, PublishResult


async def _not_implemented(platform: str) -> PublishResult:
    raise PublishError(
        f"{platform} publish not implemented yet. Open an issue or wire it up "
        f"following the protocol link in app/service/publish/_stubs.py."
    )


async def publish_tiktok(
    *, video_path: Path, metadata: PublishMetadata, token: TokenBlob,
) -> PublishResult:
    _ = (video_path, metadata, token)
    return await _not_implemented("TikTok")


async def publish_instagram(
    *, video_path: Path, metadata: PublishMetadata, token: TokenBlob,
) -> PublishResult:
    _ = (video_path, metadata, token)
    return await _not_implemented("Instagram")


async def publish_linkedin(
    *, video_path: Path, metadata: PublishMetadata, token: TokenBlob,
) -> PublishResult:
    _ = (video_path, metadata, token)
    return await _not_implemented("LinkedIn")


async def publish_x(
    *, video_path: Path, metadata: PublishMetadata, token: TokenBlob,
) -> PublishResult:
    _ = (video_path, metadata, token)
    return await _not_implemented("X")
