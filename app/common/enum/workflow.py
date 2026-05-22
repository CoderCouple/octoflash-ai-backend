"""Workflow-level enums.

NOTE: WorkflowStatus lives in `execution.py` (alongside execution lineage)
because the lifecycle is tightly coupled to runs. This file is intentionally
sparse — old NodeKind/EdgeKind were removed when the node-type library
(`workflow_node_type` table) replaced enum-based kind dispatch.
"""

from app.common.enum.execution import WorkflowStatus  # noqa: F401  (re-export)
