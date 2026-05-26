from datetime import datetime

from sqlalchemy import (
    UUID,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from uuid_utils import uuid7

from src.infrastructure.dbs.postgres.base import DBEBase


class CheckpointDBE(DBEBase):
    __tablename__ = "checkpoints"
    __table_args__ = (
        Index("idx_checkpoint_execution_id", "execution_id"),
        UniqueConstraint(
            "execution_id",
            name="uq_checkpoint_execution_id",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    execution_id = Column(
        ForeignKey(
            "executions.id",
            name="fk_checkpoint_execution_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    step_number = Column(Integer(), nullable=False)
    completed_at = Column(
        DateTime(),
        nullable=False,
    )
    state_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(), default=datetime.now)
