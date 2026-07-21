from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class StepStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: UUID
    step_number: int
    step_name: str
    output: dict[str, Any] | None = None
    cached: bool = False
    duration_ms: int | None = None
    error: dict[str, Any] | None = None


@dataclass(frozen=True)
class CheckpointResponse:
    id: UUID
    execution_id: UUID
    step_number: int
    completed_at: datetime
    state_hash: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ExecutionStep:
    step_number: int
    step_name: str
    status: str
    cached: bool
    duration_ms: int | None = None
    error: dict[str, Any] | None = None
    timestamp: str = ""


@dataclass(frozen=True)
class ExecutionHistory:
    execution_id: UUID
    workflow_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[ExecutionStep] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionInfo:
    id: UUID
    workflow_id: str
    status: str
    started_at: datetime
    initial_input: dict[str, Any] | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ResumeState:
    execution_id: UUID
    checkpoint_step: int
    reconstructed_state: dict[str, Any]
    state_hash: str | None = None
    ready_to_resume: bool = True


@dataclass(frozen=True)
class ReplayState:
    execution_id: UUID
    replay_from_step: int
    reconstructed_state: dict[str, Any]
    ready_to_resume: bool = True
