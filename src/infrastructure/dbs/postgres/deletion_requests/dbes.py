from datetime import datetime

from sqlalchemy import (
    UUID,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from uuid_utils import uuid7

from src.infrastructure.dbs.postgres.base import DBEBase


class DeletionRequestDBE(DBEBase):
    __tablename__ = "deletion_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    execution_id = Column(
        ForeignKey(
            "executions.id",
            name="fk_audit_log_execution_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    reason = Column(String(255))
    requested_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, server_default="pending")

    __table_args__ = (
        Index(
            "idx_deletion_request_status_pending",
            "status",
            postgresql_where=(status > "pending"),
        ),
        UniqueConstraint(
            "execution_id",
            name="uq_deletion_request_execution_id",
        ),
    )
