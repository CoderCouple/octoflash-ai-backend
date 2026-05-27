"""Seed a starter React Flow DAG onto a freshly-analyzed project.

Two callsites today:

  * `seed_workflow_definition_activity` — the tail of
    AnalyzeProjectWorkflow runs this after clip planning so the editor
    opens to a real graph (source_url → analyze → N scenes → target).

  * `bind_scenes_to_dag_activity` in project_activity.py — when Generate
    runs against a project whose analyze failed (so workflow.definition
    stayed null), it falls back to seeding from the Scene rows directly
    instead of leaving the canvas blank. Reuses the helper below.

The layout mirrors the FE's `seedFromScenes` constants in flow-editor.tsx
so the canvas opens in a sensible left-to-right linear shape. The target
node is connected for visual completeness but is never auto-fired by
Generate — the user must explicitly click Run on it after reviewing
rendered videos.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

import app.model  # noqa: F401  (side-effect: register all models)
from app.db.engine import get_async_engine
from app.db.repository.workflow_repository import WorkflowRepository
from app.model.workflow_edge_instance_model import WorkflowEdgeInstance
from app.model.workflow_node_instance_model import WorkflowNodeInstance


# Keep these in lockstep with flow-editor.tsx (SEED_NODE_PITCH, SEED_NODE_Y).
_NODE_PITCH = 320
_NODE_Y = 100


def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def _wni() -> str:
    return f"wni_{uuid.uuid4()}"


def _we() -> str:
    return f"we_{uuid.uuid4()}"


@dataclass
class SeedClip:
    """One planned (or materialized) clip. `scene_id` is set when bound
    to a real Scene row; left None for analyze-time seeding before any
    scenes are materialized."""
    n: int
    title: str
    prompt: str
    duration: float
    scene_id: str | None = None


@dataclass
class SeedWorkflowInput:
    workflow_id: str
    source_url: str
    clips: list[SeedClip]


# ─── shared dag builder — used by seed_workflow_definition_activity AND
#                                bind_scenes_to_dag_activity ────────────────

async def build_seed_dag(
    *,
    session: AsyncSession,
    workflow_id: str,
    source_url: str,
    clips: list[SeedClip],
) -> tuple[int, int]:
    """Build + persist a seeded DAG onto an existing Workflow row.

    Replaces any existing nodes/edges (caller is responsible for deciding
    when to call — typically only when workflow.definition is empty).
    Returns (node_count, edge_count).
    """
    repo = WorkflowRepository(session)
    workflow = await repo.get_by_id(workflow_id)
    if workflow is None:
        raise RuntimeError(f"Workflow {workflow_id} not found")

    # Resolve each node-type machine key → workflow_node_type.id. The four
    # kinds used in the seed must exist in the catalog (seeded by the SQL
    # baseline + 0002 catalog addition for 'analyze').
    type_ids: dict[str, str] = {}
    for key in ("source_url", "analyze", "scene", "target"):
        row = await repo.get_node_type_by_key(key)
        if row is None:
            raise RuntimeError(f"Catalog missing workflow_node_type {key!r}")
        type_ids[key] = row.id

    nodes_json: list[dict[str, Any]] = []
    edges_json: list[dict[str, Any]] = []
    node_rows: list[WorkflowNodeInstance] = []
    edge_rows: list[WorkflowEdgeInstance] = []

    def _node(
        *,
        nid: str,
        kind: str,
        data: dict[str, Any],
        x: float,
        y: float,
        scene_id: str | None = None,
        label: str | None = None,
    ) -> None:
        node_data: dict[str, Any] = {"type": kind, **data}
        if scene_id:
            node_data["scene_id"] = scene_id
        nodes_json.append({
            "id": nid,
            "type": "OctoflashNode",
            "dragHandle": ".drag-handle",
            "position": {"x": x, "y": y},
            "data": node_data,
        })
        node_rows.append(WorkflowNodeInstance(
            id=nid,
            workflow_id=workflow.id,
            type_id=type_ids[kind],
            scene_id=scene_id,
            x=x,
            y=y,
            label=label,
            config={k: v for k, v in data.items() if k != "type"} or None,
        ))

    def _edge(*, src: str, src_handle: str, tgt: str, tgt_handle: str) -> None:
        eid = _we()
        edges_json.append({
            "id": eid,
            "source": src,
            "sourceHandle": src_handle,
            "target": tgt,
            "targetHandle": tgt_handle,
            "animated": True,
            "type": "default",
        })
        edge_rows.append(WorkflowEdgeInstance(
            id=eid,
            workflow_id=workflow.id,
            source_instance_id=src,
            target_instance_id=tgt,
            source_handle=src_handle,
            target_handle=tgt_handle,
            label=None,
            data=None,
        ))

    source_id = _wni()
    analyze_id = _wni()
    scene_node_ids = [_wni() for _ in clips]
    target_id = _wni()

    _node(nid=source_id, kind="source_url",
          data={"inputs": {"source_url": source_url}},
          x=0, y=_NODE_Y)
    _node(nid=analyze_id, kind="analyze", data={"inputs": {}},
          x=_NODE_PITCH, y=_NODE_Y)
    _edge(src=source_id, src_handle="source", tgt=analyze_id, tgt_handle="source")

    prev_scene: str | None = None
    for i, (sid, clip) in enumerate(zip(scene_node_ids, clips)):
        _node(
            nid=sid, kind="scene",
            data={
                "inputs": {},
                "brief": clip.prompt,
                "title": clip.title,
                "duration": clip.duration,
                "n": clip.n,
            },
            x=(i + 2) * _NODE_PITCH, y=_NODE_Y,
            scene_id=clip.scene_id,
            label=clip.title,
        )
        if prev_scene is None:
            _edge(src=analyze_id, src_handle="brief", tgt=sid, tgt_handle="brief")
        else:
            _edge(src=prev_scene, src_handle="clip", tgt=sid, tgt_handle="prev")
        prev_scene = sid

    target_x = (len(scene_node_ids) + 2) * _NODE_PITCH
    _node(nid=target_id, kind="target",
          data={"inputs": {}, "target_id": None},
          x=target_x, y=_NODE_Y)
    if prev_scene is not None:
        _edge(src=prev_scene, src_handle="clip", tgt=target_id, tgt_handle="clip")

    workflow.definition = {
        "nodes": nodes_json,
        "edges": edges_json,
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }
    await repo.update(workflow)
    await repo.replace_projections(workflow_id, node_rows, edge_rows)
    return len(nodes_json), len(edges_json)


@activity.defn(name="seed_workflow_definition")
async def seed_workflow_definition_activity(payload: SeedWorkflowInput) -> None:
    """Tail of AnalyzeProjectWorkflow. Wraps `build_seed_dag` with a
    short-lived async session and commits."""
    activity.logger.info(
        "seed_workflow_definition: workflow=%s clips=%d source_url=%s",
        payload.workflow_id, len(payload.clips), payload.source_url,
    )
    factory = _session_factory()
    async with factory() as session:
        # Normalize Temporal's dataclass→dict round-trip.
        clips = [
            c if isinstance(c, SeedClip) else SeedClip(
                n=int(c["n"]),
                title=str(c["title"]),
                prompt=str(c["prompt"]),
                duration=float(c["duration"]),
                scene_id=c.get("scene_id"),
            )
            for c in payload.clips
        ]
        nodes, edges = await build_seed_dag(
            session=session,
            workflow_id=payload.workflow_id,
            source_url=payload.source_url,
            clips=clips,
        )
        await session.commit()
    activity.logger.info(
        "seed_workflow_definition: persisted %d nodes + %d edges",
        nodes, edges,
    )
