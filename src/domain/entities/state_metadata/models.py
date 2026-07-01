from datetime import datetime
from uuid import UUID

from pydantic.dataclasses import dataclass
from pydantic.fields import Field


@dataclass(slots=True)
class StateMetadataModel:
    execution_id: UUID
    compression_algorithm: str
    original_size_bytes: int
    compressed_size_bytes: int
    schema_version: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.now)
