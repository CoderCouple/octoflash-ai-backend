import uuid

from sqlalchemy import TIMESTAMP, Column, Float, ForeignKey, String, func

from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"wn_{uuid.uuid4()}"


class WorkflowNode(Base):
    __tablename__ = "workflow_node"

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    project_id = Column(String(), ForeignKey("project.id"), nullable=False, index=True)
    kind = Column(String(16), nullable=False)  # NodeKind: start/scene/branch/merge/end
    x = Column(Float, nullable=False, default=0)
    y = Column(Float, nullable=False, default=0)
    w = Column(Float, nullable=True)
    h = Column(Float, nullable=True)
    label = Column(String(255), nullable=True)
    scene_id = Column(String(), ForeignKey("scene.id"), nullable=True)
    style_override = Column(String(32), nullable=True)
    branch_label = Column(String(64), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
