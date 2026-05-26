from datetime import datetime
from uuid import UUID

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class CheckpointModel:
    id: UUID
    execution_id: UUID
    step_number: int
    completed_at: datetime
    state_hash: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
