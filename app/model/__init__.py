"""
Eagerly import every model so SQLAlchemy's metadata is complete the moment
`app.model` is imported. Used by:
  - Alembic's env.py (autogenerate needs full metadata)
  - Worker activities that open their own sessions outside the request lifecycle
  - Tests' conftest

Without this, an activity that only references one model can hit
`NoReferencedTableError` when its FKs point at tables SQLAlchemy hasn't seen yet.
"""

from app.model.billing_event_model import BillingEvent  # noqa: F401
from app.model.credential_model import Credential  # noqa: F401
from app.model.execution_log_model import ExecutionLog  # noqa: F401
from app.model.execution_phase_model import ExecutionPhase  # noqa: F401
from app.model.org_membership_model import OrgMembership  # noqa: F401
from app.model.organization_model import Organization  # noqa: F401
from app.model.project_model import Project  # noqa: F401
from app.model.scene_model import Scene  # noqa: F401
from app.model.scene_render_model import SceneRender  # noqa: F401
from app.model.source_model import Source  # noqa: F401
from app.model.source_video_model import SourceVideo  # noqa: F401
from app.model.subscription_model import Subscription  # noqa: F401
from app.model.target_model import Target  # noqa: F401
from app.model.user_model import User  # noqa: F401
from app.model.user_preference_model import UserPreference  # noqa: F401
from app.model.waitlist_model import WaitlistEntry  # noqa: F401
from app.model.workflow_edge_instance_model import WorkflowEdgeInstance  # noqa: F401
from app.model.workflow_execution_model import WorkflowExecution  # noqa: F401
from app.model.workflow_model import Workflow  # noqa: F401
from app.model.workflow_node_instance_model import WorkflowNodeInstance  # noqa: F401
from app.model.workflow_node_prop_model import WorkflowNodeProp  # noqa: F401
from app.model.workflow_node_type_model import WorkflowNodeType  # noqa: F401
from app.model.workspace_model import Workspace  # noqa: F401
