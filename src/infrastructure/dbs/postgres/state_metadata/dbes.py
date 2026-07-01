from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, ForeignKey, Integer, String

from src.infrastructure.dbs.postgres.base import DBEBase


class StateMetadataDBE(DBEBase):
    __tablename__ = "state_metadata"

    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    compression_algorithm = Column(String(50), nullable=False, default="none")
    original_size_bytes = Column(Integer(), nullable=False)
    compressed_size_bytes = Column(Integer(), nullable=False)
    schema_version = Column(
        Integer(), ForeignKey("event_schema_version.version"), default=1
    )
    created_at = Column(DateTime(), default=datetime.now)
