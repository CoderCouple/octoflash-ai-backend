import uuid

from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"we_{uuid.uuid4()}"


class WorkflowEdge(Base):
    __tablename__ = "workflow_edge"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    project_id = Column(String(), ForeignKey("project.id"), nullable=False, index=True)
    from_node_id = Column(String(), ForeignKey("workflow_node.id"), nullable=False)
    to_node_id = Column(String(), ForeignKey("workflow_node.id"), nullable=False)
    kind = Column(String(16), nullable=False, default="default")  # EdgeKind
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
