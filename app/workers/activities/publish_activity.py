"""publish_target_activity — drives the actual upload.

Wraps `publish_for_platform(...)` so a long-running platform upload runs
under Temporal's retry + heartbeat machinery rather than tying up the
FastAPI request thread.

Token refresh has already happened upstream in `PublishService.publish`;
the input carries an access_token that we expect to be valid for the
duration of the upload. (Future: heartbeat-driven refresh inside the
activity for genuinely long uploads.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from temporalio import activity

import app.model  # noqa: F401  (side-effect: register models)
from app.common.enum.target import TargetPlatform
from app.service.oauth_service import TokenBlob
from app.service.publish import PublishError, PublishMetadata, publish_for_platform


@dataclass
class PublishActivityInput:
    target_id: str
    project_id: str
    orientation: str
    platform: str             # str-value of TargetPlatform; cast in activity
    video_path: str
    access_token: str
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    privacy: str = "private"
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class PublishActivityOutput:
    platform_video_id: str
    platform_url: str


@activity.defn(name="publish_target")
async def publish_target_activity(payload: PublishActivityInput) -> PublishActivityOutput:
    activity.logger.info(
        "publish_target: platform=%s project=%s target=%s file=%s",
        payload.platform, payload.project_id, payload.target_id, payload.video_path,
    )
    try:
        platform = TargetPlatform(payload.platform)
    except ValueError as e:
        raise PublishError(f"Unknown platform {payload.platform!r}") from e

    token = TokenBlob(
        access_token=payload.access_token,
        refresh_token=None,
        expires_at=None,
        scope=None,
        token_type="Bearer",
        raw={},
    )
    metadata = PublishMetadata(
        title=payload.title,
        description=payload.description,
        tags=list(payload.tags),
        privacy=payload.privacy,
        extra={k: v for k, v in payload.extra.items()},
    )
    result = await publish_for_platform(
        platform=platform,
        video_path=Path(payload.video_path),
        metadata=metadata,
        token=token,
    )
    activity.logger.info(
        "publish_target: done platform=%s id=%s url=%s",
        payload.platform, result.platform_video_id, result.platform_url,
    )
    return PublishActivityOutput(
        platform_video_id=result.platform_video_id,
        platform_url=result.platform_url,
    )
