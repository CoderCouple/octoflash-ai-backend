"""Seed a starter React Flow DAG onto a freshly-analyzed project.

Runs at the tail of AnalyzeProjectWorkflow once clip planning is done.
Persists:
  * `workflow.definition` ← full React Flow JSON (source → analyze → N scenes → target)
  * `workflow_node_instance` + `workflow_edge_instance` projection rows

The layout mirrors the FE's `seedFromScenes` constants in flow-editor.tsx
so the canvas opens in a sensible left-to-right linear shape. The target
node is connected for visual completeness but is never auto-fired by the
generate workflow — the user must explicitly click "Run" on it after
reviewing the rendered videos.
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
    """One planned clip as the planner activity emits it (flat for Temporal)."""
    n: int
    title: str
    prompt: str
    duration: float


@dataclass
class SeedWorkflowInput:
    workflow_id: str
    source_url: str
    clips: list[SeedClip]


@activity.defn(name="seed_workflow_definition")
async def seed_workflow_definition_activity(payload: SeedWorkflowInput) -> None:
    """Build + persist the starter DAG. Idempotent — replaces any existing
    nodes/edges for the workflow."""
    activity.logger.info(
        "seed_workflow_definition: workflow=%s clips=%d source_url=%s",
        payload.workflow_id, len(payload.clips), payload.source_url,
    )

    factory = _session_factory()
    async with factory() as session:
        repo = WorkflowRepository(session)

        workflow = await repo.get_by_id(payload.workflow_id)
        if workflow is None:
            raise RuntimeError(f"Workflow {payload.workflow_id} not found")

        # Resolve each node-type key → workflow_node_type.id. The four kinds
        # used in the seed must exist in the catalog (seeded by the SQL
        # baseline + 0002 catalog addition for 'analyze').
        type_ids: dict[str, str] = {}
        for key in ("source_url", "analyze", "scene", "target"):
            row = await repo.get_node_type_by_key(key)
            if row is None:
                raise RuntimeError(f"Catalog missing workflow_node_type {key!r}")
            type_ids[key] = row.id

        # ── build the React Flow JSON shape the FE expects ──
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
            label: str | None = None,
        ) -> None:
            nodes_json.append({
                "id": nid,
                "type": "OctoflashNode",
                "dragHandle": ".drag-handle",
                "position": {"x": x, "y": y},
                "data": {"type": kind, **data},
            })
            node_rows.append(WorkflowNodeInstance(
                id=nid,
                workflow_id=workflow.id,
                type_id=type_ids[kind],
                scene_id=None,           # Phase 1: visual only, no scene rows yet
                x=x,
                y=y,
                label=label,
                config={k: v for k, v in data.items() if k != "type"} or None,
            ))

        def _edge(
            *, src: str, src_handle: str, tgt: str, tgt_handle: str,
        ) -> None:
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
        scene_ids = [_wni() for _ in payload.clips]
        target_id = _wni()

        # 1. source_url
        _node(
            nid=source_id, kind="source_url",
            data={"inputs": {"source_url": payload.source_url}},
            x=0, y=_NODE_Y,
        )
        # 2. analyze
        _node(
            nid=analyze_id, kind="analyze", data={"inputs": {}},
            x=_NODE_PITCH, y=_NODE_Y,
        )
        _edge(src=source_id, src_handle="source", tgt=analyze_id, tgt_handle="source")

        # 3. scene chain
        prev_scene: str | None = None
        for i, (sid, clip) in enumerate(zip(scene_ids, payload.clips)):
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
                label=clip.title,
            )
            if prev_scene is None:
                _edge(src=analyze_id, src_handle="brief", tgt=sid, tgt_handle="brief")
            else:
                _edge(src=prev_scene, src_handle="clip", tgt=sid, tgt_handle="prev")
            prev_scene = sid

        # 4. target — connected for visual completeness; never auto-fired.
        target_x = (len(scene_ids) + 2) * _NODE_PITCH
        _node(
            nid=target_id, kind="target",
            data={"inputs": {}, "target_id": None},
            x=target_x, y=_NODE_Y,
        )
        if prev_scene is not None:
            _edge(src=prev_scene, src_handle="clip", tgt=target_id, tgt_handle="clip")

        # ── persist ──
        workflow.definition = {
            "nodes": nodes_json,
            "edges": edges_json,
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }
        await repo.update(workflow)
        await repo.replace_projections(payload.workflow_id, node_rows, edge_rows)
        await session.commit()

    activity.logger.info(
        "seed_workflow_definition: persisted %d nodes + %d edges",
        len(nodes_json), len(edges_json),
    )
