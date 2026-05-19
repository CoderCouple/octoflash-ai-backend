"""
Resolve a project's scenes → ordered list of local clip paths for FFmpeg concat.

Per-scene selection rule:
  1. If scene.selected_variation_id is set → use that variation.
  2. Else fall back to the most recently rendered ready variation.
  3. Else fail the job with a clear error pointing at the offending scene.

URL → local path translation:
  - file://abs/path  → abs/path     (StorageService's local-FS fallback)
  - /abs/path        → /abs/path    (defensive)
  - s3://...         → not supported yet; raise so the workflow fails loudly.

Workflows can't do IO, so all DB lookups happen here.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

# Side-effect import: registers every model in metadata.
import app.model  # noqa: F401
from app.db.engine import get_async_engine
from app.model.scene_model import Scene
from app.model.variation_model import Variation


def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def _url_to_local_path(url: str, scene_id: str) -> str:
    if url.startswith("file://"):
        return url[len("file://"):]
    if url.startswith("/"):
        return url
    if url.startswith("s3://") or url.startswith("https://"):
        raise RuntimeError(
            f"Scene {scene_id}: remote video_url ({url}) not supported by concat yet — "
            "download-then-concat path is TODO."
        )
    raise RuntimeError(f"Scene {scene_id}: unrecognized video_url format: {url}")


@dataclass
class ResolveProjectClipsInput:
    project_id: str


@dataclass
class ResolvedClip:
    scene_id: str
    variation_id: str
    local_path: str
    duration: float


@dataclass
class ResolveProjectClipsOutput:
    clips: list[ResolvedClip]


@activity.defn(name="resolve_project_clips")
async def resolve_project_clips_activity(
    payload: ResolveProjectClipsInput,
) -> ResolveProjectClipsOutput:
    """Build the ordered clip list for a project, ready for FFmpeg concat."""
    factory = _session_factory()
    async with factory() as session:
        scene_rows = (
            await session.execute(
                select(Scene)
                .where(Scene.project_id == payload.project_id)
                .order_by(Scene.n.asc())
            )
        ).scalars().all()

        if not scene_rows:
            raise RuntimeError(f"Project {payload.project_id} has no scenes")

        clips: list[ResolvedClip] = []
        for scene in scene_rows:
            variation: Variation | None = None

            if scene.selected_variation_id:
                variation = (
                    await session.execute(
                        select(Variation).where(Variation.id == scene.selected_variation_id)
                    )
                ).scalar_one_or_none()
                if variation is None:
                    raise RuntimeError(
                        f"Scene {scene.id}: selected_variation_id "
                        f"{scene.selected_variation_id} not found"
                    )
            else:
                # Fallback — most recently rendered ready variation.
                variation = (
                    await session.execute(
                        select(Variation)
                        .where(Variation.scene_id == scene.id, Variation.status == "ready")
                        .order_by(Variation.rendered_at.desc().nullslast())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if variation is None:
                    raise RuntimeError(
                        f"Scene {scene.id} ({scene.template}) has no rendered variations — "
                        "render it first via POST /scenes/{id}/variations"
                    )

            if not variation.video_url:
                raise RuntimeError(
                    f"Scene {scene.id} variation {variation.id} has no video_url yet"
                )

            local_path = _url_to_local_path(variation.video_url, scene.id)
            clips.append(
                ResolvedClip(
                    scene_id=scene.id,
                    variation_id=variation.id,
                    local_path=local_path,
                    duration=variation.duration or 0.0,
                )
            )

        activity.logger.info(
            "resolve_project_clips: project=%s resolved %d clip(s)",
            payload.project_id,
            len(clips),
        )
        return ResolveProjectClipsOutput(clips=clips)
