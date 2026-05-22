"""WorkflowNodeProp — per-node-type prop schema (key/default/group/type)."""

import uuid

from sqlalchemy import TIMESTAMP, Column, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum

from app.common.enum.workflow_node import NodePropGroup, NodePropType
from app.db.base import Base


def generate_prefixed_uuid() -> str:
    return f"nprop_{uuid.uuid4()}"


class WorkflowNodeProp(Base):
    __tablename__ = "workflow_node_prop"
    __table_args__ = (
        UniqueConstraint("node_id", "key", name="uq_workflow_node_prop_node_key"),
    )

    id = Column(String(), primary_key=True, default=generate_prefixed_uuid, nullable=False)
    node_id = Column(
        String(),
        ForeignKey("workflow_node_type.id", ondelete="CASCADE"),
        nullable=False,
    )
    key = Column(String(100), nullable=False)
    value = Column(Text(), nullable=False)
    prop_group = Column(
        SAEnum(
            NodePropGroup,
            name="node_prop_group_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
    )
    type = Column(
        SAEnum(
            NodePropType,
            name="node_prop_type_enum",
            create_type=False,
            values_callable=lambda e: [v.value for v in e],
        ),
        nullable=False,
    )
    created_by = Column(String(), ForeignKey("user.id"), nullable=True)
    updated_by = Column(String(), ForeignKey("user.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
