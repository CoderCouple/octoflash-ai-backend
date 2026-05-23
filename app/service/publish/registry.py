"""Platform → publisher dispatch table.

Adding a 6th platform = drop a `publish(...)` async function in a new module
and add one entry below.
"""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable

from app.common.enum.target import TargetPlatform
from app.service.oauth_service import TokenBlob
from app.service.publish._stubs import (
    publish_instagram,
    publish_linkedin,
    publish_tiktok,
    publish_x,
)
from app.service.publish.models import PublishMetadata, PublishResult
from app.service.publish.youtube import publish as publish_youtube


_Publisher = Callable[..., Awaitable[PublishResult]]


PUBLISHERS: dict[TargetPlatform, _Publisher] = {
    TargetPlatform.YOUTUBE:   publish_youtube,
    TargetPlatform.TIKTOK:    publish_tiktok,
    TargetPlatform.INSTAGRAM: publish_instagram,
    TargetPlatform.LINKEDIN: publish_linkedin,
    TargetPlatform.X:        publish_x,
}


async def publish_for_platform(
    *,
    platform: TargetPlatform,
    video_path: Path,
    metadata: PublishMetadata,
    token: TokenBlob,
) -> PublishResult:
    """Route to the platform's publisher. KeyError = unregistered platform."""
    publisher = PUBLISHERS[platform]
    return await publisher(video_path=video_path, metadata=metadata, token=token)
