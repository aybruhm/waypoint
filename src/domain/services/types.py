from typing import Any, Dict
from uuid import UUID

from pydantic.fields import Field
from pydantic.dataclasses import dataclass

# ---- Events types


ConstructedState = Dict[str, Any]


@dataclass(frozen=True)
class EventCreateData:
    step_name: str
    status: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any] | None = None
    side_effects: Dict[str, Any] | None = None
    error: Dict[str, Any] | None = None
    duration_ms: int | None = None
    cached: bool = Field(default=False)


# ---- Replay Engine types


@dataclass(frozen=True)
class State:
    execution_id: UUID
    reconstructed_state: ConstructedState
    ready_to_resume: bool


@dataclass(frozen=True, slots=True)
class CheckpointState(State):
    checkpoint_step: int
    state_hash: str


@dataclass(frozen=True, slots=True)
class ReplayState(State):
    replay_from_state: int
