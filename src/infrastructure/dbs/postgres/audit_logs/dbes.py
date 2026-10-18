from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from uuid_utils import uuid7

from src.infrastructure.dbs.postgres.base import DBEBase


class AuditLogDBE(DBEBase):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index(
            "idx_audit_execution_action",
            "execution_id",
            "action",
            postgresql_ops={"created_at": "DESC"},
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    execution_id = Column(
        ForeignKey(
            "executions.id",
            name="fk_audit_log_execution_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    action = Column(String(50), nullable=False)
    actor_id = Column(String(255))
    details = Column(
        mutable_json_type(dbtype=JSONB, nested=True),
        nullable=False,
        default=dict,
    )
    created_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
