"""
Project / Scene DB-write activities — status updates, brief persistence,
clip creation, hash cache reads.

Each activity opens its own short-lived async session so Temporal can retry
independently of FastAPI's request lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

# Side-effect import so Base.metadata has every model registered.
import app.model  # noqa: F401
from app.db.engine import get_async_engine
from app.db.repository.project_repository import ProjectRepository
from app.db.repository.scene_repository import SceneRepository
from app.model.scene_model import Scene


def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# ─── update project status / fields ──────────────────────────────────────────


@dataclass
class UpdateProjectInput:
    project_id: str
    status: str | None = None
    title: str | None = None
    transcript: str | None = None
    description: str | None = None
    manim_prompt: str | None = None
    source_duration: float | None = None
    frames_dir: str | None = None
    final_portrait_video_url: str | None = None
    final_landscape_video_url: str | None = None


@activity.defn(name="update_project")
async def update_project_activity(payload: UpdateProjectInput) -> None:
    """Patch a Project row with whatever non-None fields are in the payload."""
    factory = _session_factory()
    async with factory() as session:
        repo = ProjectRepository(session)
        project = await repo.get_by_id(payload.project_id)
        if project is None:
            activity.logger.warning("update_project: project %s not found", payload.project_id)
            return

        changed = []
        for field_name in (
            "status", "title", "transcript", "description", "manim_prompt",
            "source_duration", "frames_dir",
            "final_portrait_video_url", "final_landscape_video_url",
        ):
            value = getattr(payload, field_name)
            if value is not None:
                setattr(project, field_name, value)
                changed.append(field_name)

        project.updated_at = datetime.utcnow()
        await repo.update(project)
        await session.commit()
        activity.logger.info(
            "update_project: project=%s fields=%s",
            payload.project_id, changed,
        )


# ─── create N Scene rows from a list of planned clip dicts ────────────────────


@dataclass
class PlannedClipDict:
    n: int
    title: str
    prompt: str
    duration: float


@dataclass
class CreateScenesInput:
    project_id: str
    clips: list[PlannedClipDict]
    orientation: str = "portrait"  # which orientation these scenes are for


@dataclass
class CreatedScene:
    scene_id: str
    n: int
    title: str
    prompt: str
    duration: float


@dataclass
class CreateScenesOutput:
    scenes: list[CreatedScene]


@dataclass
class BindScenesToDagInput:
    """Bind freshly-materialized Scene rows back to the seeded DAG nodes.

    `seed_workflow_definition_activity` (run at the tail of analyze) creates
    placeholder scene nodes with `data.scene_id=null` because there are no
    Scene rows yet. When Generate runs and creates the actual scene rows,
    this activity walks the DAG and stitches each node to its scene row
    (matching on `data.n`), updating both the JSONB definition and the
    projection FK.

    Binding makes the FE's click→preview path resolve cleanly via
    `data.scene_id` without falling back to n-matching heuristics.

    Idempotent: only binds nodes whose `data.scene_id` is currently null,
    so a re-run of Generate (or generating the second orientation) doesn't
    clobber the existing binding.
    """
    project_id: str
    orientation: str
    scenes: list[CreatedScene]


@dataclass
class BindScenesToDagOutput:
    bound_count: int


@activity.defn(name="bind_scenes_to_dag")
async def bind_scenes_to_dag_activity(
    payload: BindScenesToDagInput,
) -> BindScenesToDagOutput:
    from app.db.repository.workflow_repository import WorkflowRepository
    from sqlalchemy import update
    from app.model.workflow_node_instance_model import WorkflowNodeInstance

    factory = _session_factory()
    async with factory() as session:
        workflow_repo = WorkflowRepository(session)
        workflow = await workflow_repo.get_by_project_id(payload.project_id)
        if workflow is None or not workflow.definition:
            activity.logger.info(
                "bind_scenes_to_dag: project=%s has no workflow definition — skipping",
                payload.project_id,
            )
            return BindScenesToDagOutput(bound_count=0)

        # Build the n → scene_id map from the freshly-created scenes.
        # Normalize for Temporal's dataclass→dict round-trip.
        n_to_scene_id: dict[int, str] = {}
        for s in payload.scenes:
            if isinstance(s, dict):
                n_to_scene_id[int(s["n"])] = str(s["scene_id"])
            else:
                n_to_scene_id[s.n] = s.scene_id

        # Walk the JSONB definition, patch in scene_id where unbound.
        # SQLAlchemy can't track in-place mutation of a JSONB column; rebuild
        # the dict so the dirty check fires.
        defn = dict(workflow.definition)
        nodes = list(defn.get("nodes", []))
        bound_node_to_scene: dict[str, str] = {}     # wni_id → scene_id
        for i, raw_node in enumerate(nodes):
            node = dict(raw_node)
            data = dict(node.get("data") or {})
            if data.get("type") != "scene":
                continue
            if data.get("scene_id"):                  # already bound (first-wins)
                continue
            n = data.get("n")
            if n is None or int(n) not in n_to_scene_id:
                continue
            scene_id = n_to_scene_id[int(n)]
            data["scene_id"] = scene_id
            node["data"] = data
            nodes[i] = node
            bound_node_to_scene[str(node["id"])] = scene_id

        if not bound_node_to_scene:
            activity.logger.info(
                "bind_scenes_to_dag: project=%s orientation=%s — nothing to bind "
                "(no matching unbound scene nodes)",
                payload.project_id, payload.orientation,
            )
            return BindScenesToDagOutput(bound_count=0)

        defn["nodes"] = nodes
        workflow.definition = defn
        await workflow_repo.update(workflow)

        # Mirror into the projection table (workflow_node_instance.scene_id).
        for wni_id, scene_id in bound_node_to_scene.items():
            await session.execute(
                update(WorkflowNodeInstance)
                .where(WorkflowNodeInstance.id == wni_id)
                .values(scene_id=scene_id)
            )
        await session.commit()
        activity.logger.info(
            "bind_scenes_to_dag: project=%s orientation=%s bound=%d",
            payload.project_id, payload.orientation, len(bound_node_to_scene),
        )
        return BindScenesToDagOutput(bound_count=len(bound_node_to_scene))


@activity.defn(name="create_scenes")
async def create_scenes_activity(payload: CreateScenesInput) -> CreateScenesOutput:
    """Persist N planned clips as Scene rows. Returns the assigned scene_ids."""
    factory = _session_factory()
    async with factory() as session:
        scene_repo = SceneRepository(session)
        created: list[CreatedScene] = []
        for spec in payload.clips:
            # Normalize: Temporal serializes dataclasses to dict round-trip
            if isinstance(spec, dict):
                n = int(spec.get("n", len(created) + 1))
                title = str(spec.get("title", f"Clip {n}"))
                prompt = str(spec.get("prompt", ""))
                duration = float(spec.get("duration", 8.0))
            else:
                n, title, prompt, duration = spec.n, spec.title, spec.prompt, spec.duration

            scene = Scene(
                project_id=payload.project_id,
                orientation=payload.orientation,
                n=n,
                title=title,
                prompt=prompt,
                duration=duration,
                status="draft",
            )
            scene = await scene_repo.create(scene)
            created.append(CreatedScene(
                scene_id=scene.id, n=n, title=title, prompt=prompt, duration=duration,
            ))

        await session.commit()
        activity.logger.info(
            "create_scenes: project=%s created=%d", payload.project_id, len(created),
        )
        return CreateScenesOutput(scenes=created)


# ─── persist a clip's render result onto its Scene row ───────────────────────


@dataclass
class PersistClipResultInput:
    scene_id: str
    script_code: str
    script_code_hash: str
    script_file: str
    video_url: str
    render_method: str
    eval_score: int | None
    eval_feedback: str | None
    status: str = "ready"


@activity.defn(name="persist_clip_result")
async def persist_clip_result_activity(payload: PersistClipResultInput) -> None:
    """After a successful render, write the script + MP4 URL onto the Scene row."""
    factory = _session_factory()
    async with factory() as session:
        scene_repo = SceneRepository(session)
        scene = await scene_repo.get_by_id(payload.scene_id)
        if scene is None:
            activity.logger.warning("persist_clip_result: scene %s not found", payload.scene_id)
            return

        scene.script_code = payload.script_code
        scene.script_code_hash = payload.script_code_hash
        scene.script_file = payload.script_file
        scene.video_url = payload.video_url
        scene.render_method = payload.render_method
        scene.eval_score = payload.eval_score
        scene.eval_feedback = payload.eval_feedback
        scene.status = payload.status
        scene.updated_at = datetime.utcnow()
        await scene_repo.update(scene)
        await session.commit()
        activity.logger.info(
            "persist_clip_result: scene=%s status=%s method=%s",
            payload.scene_id, payload.status, payload.render_method,
        )


# ─── read existing Scene for cache lookup ────────────────────────────────────


@dataclass
class GetSceneCacheInput:
    scene_id: str


@dataclass
class GetSceneCacheOutput:
    script_code: str | None
    script_code_hash: str | None
    video_url: str | None


@activity.defn(name="get_scene_cache")
async def get_scene_cache_activity(payload: GetSceneCacheInput) -> GetSceneCacheOutput:
    """Read cache-relevant fields for the skip-if-unchanged path."""
    factory = _session_factory()
    async with factory() as session:
        scene_repo = SceneRepository(session)
        scene = await scene_repo.get_by_id(payload.scene_id)
        if scene is None:
            return GetSceneCacheOutput(script_code=None, script_code_hash=None, video_url=None)
        return GetSceneCacheOutput(
            script_code=scene.script_code,
            script_code_hash=scene.script_code_hash,
            video_url=scene.video_url,
        )


# ─── small helper: tell the Path string from a Scene.video_url ───────────────


def video_path(video_url: str | None) -> Path | None:
    """If video_url looks like a local disk path, return as Path; else None.

    The activity layer stores file:// or absolute paths in v1. S3 URLs will
    return None and the cache check just won't fire.
    """
    if not video_url:
        return None
    if video_url.startswith(("http://", "https://", "s3://")):
        return None
    return Path(video_url)
