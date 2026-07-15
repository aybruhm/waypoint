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


class EventSchemaVersionDBE(DBEBase):
    __tablename__ = "event_schema_version"

    id = Column(UUID(as_uuid=True), default=uuid7)
    version = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    schema_definition = Column(
        mutable_json_type(dbtype=JSONB, nested=True),
        nullable=False,
        default=dict,
    )
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    deprecated_at = Column(DateTime)


class EventDBE(DBEBase):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_event_execution_id", "execution_id"),
        Index("idx_event_schema_version", "schema_version"),
        Index("idx_event_compression", "compression_algorithm"),
        # -------------------------------------------------------------------
        # Learn more about composite and covering index with Postgres here:
        # ---- https://www.opcito.com/blogs/a-guide-to-postgresql-indexing-with-sqlalchemy
        # -------------------------------------------------------------------
        Index(
            "idx_event_execution_step_cover",
            "execution_id",
            "step_number",
            postgresql_include=[
                "status",
                "cached",
                "duration_ms",
            ],
        ),
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
    schema_version = Column(
        ForeignKey(
            "event_schema_version.version",
            name="fk_event_schema_version",
            ondelete="CASCADE",
        ),
        default=1,
    )
    state_size_original_bytes = Column(Integer, default=0)
    state_size_compressed_bytes = Column(Integer, default=0)
    compression_algorithm = Column(String(50), default="none")
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
