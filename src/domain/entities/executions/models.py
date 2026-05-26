from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import Field
from pydantic.dataclasses import dataclass

from src.domain.shared.types import EXECUTION_STATUSES


@dataclass(slots=True)
class ExecutionModel:
    id: UUID
    agent_id: str
    status: EXECUTION_STATUSES
    started_at: datetime
    completed_at: datetime | None = None
    initial_input: Dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
