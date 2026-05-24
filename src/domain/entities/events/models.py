from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic.dataclasses import dataclass, field

from src.domain.shared.types import EVENT_STATUSES


@dataclass(slots=True)
class EventModel:
    id: UUID
    execution_id: UUID
    step_number: int
    step_name: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    status: EVENT_STATUSES
    side_effects: Dict[str, Any] | None = None
    cached: bool = False
    error: Dict[str, Any] | None = None
    duration_ms: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
