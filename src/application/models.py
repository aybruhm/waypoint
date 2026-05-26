from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field


class CreateExecutionRequest(BaseModel):
    agent_id: str
    initial_input: Dict[str, Any] | None = None


class CreateExecutionResponse(BaseModel):
    id: UUID
    agent_id: str
    status: str
    started_at: datetime
    initial_input: Dict[str, Any] | None = None
    created_at: datetime


class ReplayFromStepRequest(BaseModel):
    step_number: int


class ExecutionStep(BaseModel):
    step_number: int
    step_name: str
    status: str
    cached: bool
    duration_ms: int | None = None
    error: Dict[str, Any] | None = None
    timestamp: str


class ExecutionHistoryResponse(BaseModel):
    execution_id: UUID
    agent_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[ExecutionStep] = Field(
        description="List of step events with step_number, step_name, status, cached, duration_ms, error"
    )


class CreateCheckpointRequest(BaseModel):
    execution_id: UUID
    step_number: int
    step_name: str
    state: Dict[str, Any]
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] | None = None
    status: str = "completed"
    duration_ms: int | None = None
    error: Dict[str, Any] | None = None
    cached: bool = False


class LoadStateFromCheckpointRequest(BaseModel):
    execution_id: UUID
    step_number: int


class CheckpointResponse(BaseModel):
    id: UUID
    execution_id: UUID
    step_number: int
    completed_at: datetime
    state_hash: str | None = None
    created_at: datetime


class CheckpointStateResponse(BaseModel):
    step_name: str
    output: Dict[str, Any]
