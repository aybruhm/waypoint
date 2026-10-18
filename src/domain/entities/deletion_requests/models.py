from datetime import datetime
from uuid import UUID

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class DeletionRequestModel:
    execution_id: UUID
    reason: str = "user_request"
    status: str = "pending"
    id: UUID | None = None
    requested_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
