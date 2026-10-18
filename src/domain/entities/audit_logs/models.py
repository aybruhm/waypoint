from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class AuditLogModel:
    execution_id: UUID
    action: str
    id: UUID | None = None
    actor_id: str = "system"
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
