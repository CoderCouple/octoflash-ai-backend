"""Per-platform publish dispatchers.

Each platform exposes a single async function

    async def publish(*, video_path: Path, metadata: PublishMetadata,
                      token: TokenBlob) -> PublishResult

Symmetric per platform; the difference is the network protocol they speak
(Resumable Upload, Content Posting API, Graph media-container, ugcPosts,
chunked v1.1 media). The OAuth dance happens upstream — by the time we
reach here the caller has already loaded + refreshed the token via
`app.service.oauth_refresh.load_fresh_token`.
"""

from app.service.publish.models import PublishMetadata, PublishResult, PublishError
from app.service.publish.registry import PUBLISHERS, publish_for_platform

__all__ = [
    "PublishMetadata",
    "PublishResult",
    "PublishError",
    "PUBLISHERS",
    "publish_for_platform",
]
