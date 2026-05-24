"""
Activity registry. The worker imports `ALL_ACTIVITIES` and registers them.

Activities are where side-effectful work happens (Claude calls, Manim render,
ffmpeg, S3 upload, DB writes). Temporal retries each per its `RetryPolicy`
on failure. Workflows compose activities — they're deterministic orchestrators
and must not do IO themselves.
"""

from app.workers.activities.analyze_activity import analyze_source_activity
from app.workers.activities.db_activity import update_execution_activity
from app.workers.activities.ffmpeg_concat_activity import ffmpeg_concat_activity
from app.workers.activities.generate_clip_activity import generate_clip_activity
from app.workers.activities.plan_activity import plan_clips_activity
from app.workers.activities.project_activity import (
    bind_scenes_to_dag_activity,
    create_scenes_activity,
    get_scene_cache_activity,
    persist_clip_result_activity,
    update_project_activity,
)
from app.workers.activities.publish_activity import publish_target_activity
from app.workers.activities.seed_workflow_activity import seed_workflow_definition_activity

ALL_ACTIVITIES = [
    # Analyze pipeline
    analyze_source_activity,
    # Plan + persist
    plan_clips_activity,
    create_scenes_activity,
    bind_scenes_to_dag_activity,
    # Per-clip generate (fans out via asyncio.gather)
    generate_clip_activity,
    get_scene_cache_activity,
    persist_clip_result_activity,
    # Stitch
    ffmpeg_concat_activity,
    # Project + execution-lineage status writes
    update_project_activity,
    update_execution_activity,
    # Seed the React Flow DAG at end of analyze
    seed_workflow_definition_activity,
    # Publish final render to a Target platform
    publish_target_activity,
]
