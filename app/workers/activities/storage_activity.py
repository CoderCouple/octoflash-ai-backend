"""S3 uploads — with a local-filesystem fallback when no AWS creds are set.

The fallback writes to `<settings.manim_output_dir>/uploads/<key>` and returns
a `file://` URL. That way the variation workflow completes end-to-end in pure
local dev (no AWS account needed) and you can still play the MP4 with VLC etc.

Switching to real S3 is automatic when the boto3 credential chain finds keys
(env vars, ~/.aws/credentials, ECS task role, etc.) AND `settings.s3_bucket_renders`
points at a real bucket.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from temporalio import activity

from app.settings import settings


@dataclass
class UploadRenderInput:
    local_path: str
    key: str
    bucket: str | None = None  # None → settings.s3_bucket_renders


def _has_aws_creds() -> bool:
    """Cheap check before pulling aioboto3. True only if explicit env keys are set."""
    return bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_SESSION_TOKEN")
        or os.getenv("AWS_PROFILE")
    )


async def _upload_to_s3(local_path: str, key: str, bucket: str) -> str:
    import aioboto3

    session = aioboto3.Session()
    async with session.client("s3", region_name=settings.aws_region) as s3:
        await s3.upload_file(local_path, bucket, key)
    if settings.s3_public_base_url:
        return f"{settings.s3_public_base_url.rstrip('/')}/{key}"
    return f"s3://{bucket}/{key}"


def _upload_to_local(local_path: str, key: str) -> str:
    """Copy into the worker's upload dir; return a file:// URL."""
    target_dir = os.path.join(os.path.abspath(settings.manim_output_dir), "uploads")
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, key.replace("/", "_"))
    # Move (not copy) — we own the temp render file after a successful upload step.
    shutil.move(local_path, target_path)
    return f"file://{target_path}"


@activity.defn(name="upload_render")
async def upload_render_activity(payload: UploadRenderInput) -> str:
    """Upload one rendered MP4. Returns the URL stored on Variation.video_url."""
    activity.heartbeat({"phase": "upload_start", "key": payload.key})

    bucket = payload.bucket or settings.s3_bucket_renders
    use_s3 = bool(bucket) and _has_aws_creds()

    if use_s3:
        url = await _upload_to_s3(payload.local_path, payload.key, bucket)
        activity.logger.info("Uploaded to S3: %s", url)
        return url

    url = _upload_to_local(payload.local_path, payload.key)
    activity.logger.info("Local FS fallback (no AWS creds): %s", url)
    return url
