from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, Enum, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from uuid_utils import uuid7

from src.infrastructure.dbs.postgres.base import DBEBase
from src.infrastructure.dbs.shared.enums import ExecutionStatus


class ExecutionDBE(DBEBase):
    __tablename__ = "executions"
    __table_args__ = (
        Index("idx_execution_workflow_id", "workflow_id"),
        Index("idx_execution_status", "status"),
        Index("idx_execution_created_at", "created_at"),
        Index("idx_execution_deleted_at", "deleted_at"),
        # -------------------------------------------------------------------
        # Learn more about composite and covering index with Postgres here:
        # ---- https://www.opcito.com/blogs/a-guide-to-postgresql-indexing-with-sqlalchemy
        # -------------------------------------------------------------------
        Index(
            "idx_execution_status_created",
            "status",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    workflow_id = Column(String(255), nullable=False)
    status = Column(
        Enum(ExecutionStatus, name="execution_status_enum_types"), nullable=False
    )
    started_at = Column(DateTime(), default=datetime.now)
    completed_at = Column(
        DateTime(),
        nullable=True,
    )
    execution_mode = Column(
        String(50),
        nullable=False,
        default="standard",
    )
    initial_input = Column(
        mutable_json_type(dbtype=JSONB, nested=True),
        nullable=False,
        default=dict,
    )
    created_at = Column(DateTime(), default=datetime.now)
    updated_at = Column(DateTime(), default=datetime.now)
    deleted_at = Column(DateTime(), default=datetime.now)
