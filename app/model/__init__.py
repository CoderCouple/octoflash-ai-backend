"""
Eagerly import every model so SQLAlchemy's metadata is complete the moment
`app.model` is imported. Used by:
  - Alembic's env.py (autogenerate needs full metadata)
  - Worker activities that open their own sessions outside the request lifecycle
  - Tests' conftest

Without this, an activity that only references one model can hit
`NoReferencedTableError` when its FKs point at tables SQLAlchemy hasn't seen yet.
"""

from app.model.channel_model import Channel  # noqa: F401
from app.model.channel_video_model import ChannelVideo  # noqa: F401
from app.model.job_model import Job  # noqa: F401
from app.model.project_model import Project  # noqa: F401
from app.model.scene_instruction_model import SceneInstruction  # noqa: F401
from app.model.scene_model import Scene  # noqa: F401
from app.model.variation_model import Variation  # noqa: F401
from app.model.workflow_edge_model import WorkflowEdge  # noqa: F401
from app.model.workflow_node_model import WorkflowNode  # noqa: F401
