from datetime import datetime

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from uuid_utils import uuid7

from src.infrastructure.dbs.postgres.base import DBEBase
from src.infrastructure.dbs.shared.enums import EventStatus


class EventDBE(DBEBase):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_event_execution_id", "execution_id"),
        Index(
            "idx_event_step_number",
            "execution_id",
            "step_number",
        ),
        Index("idx_event_status", "status"),
        Index("idx_event_created_at", "created_at"),
        UniqueConstraint(
            "execution_id",
            "step_number",
            name="uq_event_execution_id_step_number",
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
            name="fk_event_execution_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    step_number = Column(Integer(), nullable=False)
    step_name = Column(String(255), nullable=False)
    input = Column(
        mutable_json_type(dbtype=JSONB, nested=True),
        nullable=False,
        default=dict,
    )
    output = Column(
        mutable_json_type(dbtype=JSONB, nested=True),
        nullable=False,
        default=dict,
    )
    side_effects = Column(
        mutable_json_type(dbtype=JSONB, nested=True),
        nullable=False,
        default=dict,
    )
    cached = Column(
        Boolean(),
        nullable=False,
        default=False,
    )
    status = Column(
        Enum(
            EventStatus,
            name="event_execution_status_enum_type",
        ),
        nullable=False,
    )
    error = Column(
        mutable_json_type(dbtype=JSONB, nested=True),
        nullable=False,
        default=dict,
    )
    duration_ms = Column(Integer(), nullable=False)
    created_at = Column(DateTime(), default=datetime.now)
