"""
Activity registry. The worker imports `ALL_ACTIVITIES` and registers them.

Activities are where side-effectful work happens (Manim render, FFmpeg, S3
upload, DB writes, HTTP calls). Each is automatically retried by Temporal
per its `RetryPolicy` if it raises. Workflows compose activities — they're
deterministic orchestrators and must not do IO themselves.
"""

from app.workers.activities.clip_resolve_activity import (
    resolve_project_clips_activity,
)
from app.workers.activities.db_activity import (
    insert_variation_activity,
    update_job_activity,
)
from app.workers.activities.ffmpeg_activity import concat_clips_activity
from app.workers.activities.render_activity import render_variation_activity
from app.workers.activities.storage_activity import upload_render_activity
from app.workers.activities.whisper_activity import (
    download_audio_activity,
    transcribe_audio_activity,
)

ALL_ACTIVITIES = [
    render_variation_activity,
    upload_render_activity,
    concat_clips_activity,
    download_audio_activity,
    transcribe_audio_activity,
    update_job_activity,
    insert_variation_activity,
    resolve_project_clips_activity,
]
