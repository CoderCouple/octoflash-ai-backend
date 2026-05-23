"""YouTube publish — Resumable Upload via googleapiclient.

The YouTube Data API v3 takes:
  POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
  Authorization: Bearer <access_token>
  body: { snippet: {title, description, tags, categoryId}, status: {privacyStatus} }
  → 200 with a Location header that we PUT chunks of the local file to.

`googleapiclient.discovery.build('youtube','v3', credentials=…)` wraps that
and the chunked upload via `MediaFileUpload(resumable=True)`. We run the
upload as a blocking `next_chunk()` loop in a worker thread — Temporal
activity wrapping makes it durable.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.service.oauth_service import TokenBlob
from app.service.publish.models import PublishError, PublishMetadata, PublishResult

log = logging.getLogger(__name__)


# Default YouTube category id when the caller doesn't specify one.
# 27 = "Education" — a sensible default for Manim animation videos.
_DEFAULT_CATEGORY_ID = "27"


async def publish(
    *,
    video_path: Path,
    metadata: PublishMetadata,
    token: TokenBlob,
) -> PublishResult:
    if not video_path.exists():
        raise PublishError(f"Video file not found: {video_path}")

    privacy = metadata.privacy if metadata.privacy in {"public", "unlisted", "private"} else "private"
    category_id = str(metadata.extra.get("categoryId", _DEFAULT_CATEGORY_ID))

    request_body = {
        "snippet": {
            "title":       metadata.title[:100],          # YT hard limit
            "description": metadata.description[:5000],   # YT hard limit
            "tags":        metadata.tags[:30],            # YT soft limit
            "categoryId":  category_id,
        },
        "status": {
            "privacyStatus":         privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    def _upload_blocking() -> dict:
        """Inner blocking call — runs in a worker thread.

        Build a one-shot YouTube client from the access token alone (no
        refresh inside this call — token refresh already happened upstream
        in `oauth_refresh.load_fresh_token`).
        """
        creds = Credentials(token=token.access_token)
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        media = MediaFileUpload(
            str(video_path),
            chunksize=-1,                # send in one chunk; fine for <100MB clips
            resumable=True,
            mimetype="video/mp4",
        )
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media,
        )
        response: dict | None = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                log.info(
                    "youtube.publish: %d%% uploaded (%s)",
                    int(status.progress() * 100), video_path.name,
                )
        return response

    try:
        response = await asyncio.to_thread(_upload_blocking)
    except HttpError as e:
        raise PublishError(
            f"YouTube upload failed: HTTP {e.resp.status} {e.error_details or e}"
        ) from e

    video_id = response.get("id") or ""
    if not video_id:
        raise PublishError(f"YouTube upload completed but no video id returned: {response}")
    return PublishResult(
        platform_video_id=video_id,
        platform_url=f"https://www.youtube.com/watch?v={video_id}",
        raw=response,
    )
