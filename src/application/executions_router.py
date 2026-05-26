import traceback
from uuid import UUID

from dataclasses import asdict

from fastapi import APIRouter, Query, Request
from fastapi.exceptions import HTTPException

from src.application.models import (
    CreateExecutionRequest,
    CreateExecutionResponse,
    ExecutionHistoryResponse,
    ExecutionStep,
    ReplayFromStepRequest,
)
from src.domain.exceptions import CheckpointNotFoundError
from src.domain.services.events_service import EventService
from src.domain.services.executions_service import ExecutionService
from src.domain.services.replay_engine import ReplayEngine


class ExecutionAPIRouter:
    def __init__(
        self,
        replay_engine: ReplayEngine,
        events_service: EventService,
        executions_service: ExecutionService,
    ) -> None:
        self.replay_engine = replay_engine
        self.events_service = events_service
        self.executions_service = executions_service

        self.router = APIRouter()

        # Register routes
        self.router.add_api_route(
            "/",
            endpoint=self.create_execution,
            methods=["POST"],
            response_model=CreateExecutionResponse,
        )
        self.router.add_api_route(
            "/{execution_id}/history",
            endpoint=self.get_execution_history,
            methods=["GET"],
            response_model=ExecutionHistoryResponse,
        )
        self.router.add_api_route(
            "/{execution_id}/resume",
            endpoint=self.resume_execution,
            methods=["POST"],
            response_model=dict,
        )
        self.router.add_api_route(
            "/{execution_id}/replay",
            endpoint=self.replay_from_step,
            methods=["POST"],
            response_model=dict,
        )

    async def create_execution(
        self,
        request: Request,
        body: CreateExecutionRequest,
    ):
        try:
            execution = await self.executions_service.create_execution(
                agent_id=body.agent_id,
                initial_input=body.initial_input,
            )
            return CreateExecutionResponse(
                id=execution.id,
                agent_id=execution.agent_id,
                status=execution.status,
                started_at=execution.started_at,
                initial_input=execution.initial_input,
                created_at=execution.created_at,
            )
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, detail=str(e))

    async def get_execution_history(
        self,
        request: Request,
        execution_id: UUID,
        offset: int = Query(0),
        limit: int = Query(100),
    ):
        try:
            steps: list[ExecutionStep] = []
            events = await self.events_service.list_events(
                execution_id=execution_id,
                offset=offset,
                limit=limit,
            )
            for event in events:
                steps.append(
                    ExecutionStep(
                        step_number=event.step_number,
                        step_name=event.step_name,
                        status=event.status,
                        cached=event.cached,
                        duration_ms=event.duration_ms,
                        error=event.error,
                        timestamp=event.created_at.isoformat(),
                    )
                )
        except Exception as e:
            raise HTTPException(500, detail=str(e))

    async def resume_execution(
        self,
        request: Request,
        execution_id: UUID,
        offset: int = Query(0),
        limit: int = Query(100),
    ):
        """
        Resume execution from the last checkpoint.

        This endpoint should be called after a crash is detected.
        It returns the reconstructed state and checkpoint info.

        The agent code should then call the next step function with this state.
        """

        try:
            result = await self.replay_engine.replay_from_checkpoint(
                execution_id,
                offset=offset,
                limit=limit,
            )
            return asdict(result)
        except CheckpointNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def replay_from_step(
        self,
        request: Request,
        execution_id: UUID,
        step_request: ReplayFromStepRequest,
        offset: int = Query(0),
        limit: int = Query(100),
    ):
        """
        Replay from a specific step (for testing and debugging).

        This allows you to re-run from an arbitrary step without waiting for a crash.
        Useful for "what if" analysis: replay from step 5 and trace through to the end.
        """

        try:
            result = await self.replay_engine.replay_from_step(
                execution_id=execution_id,
                step_number=step_request.step_number,
                offset=offset,
                limit=limit,
            )
            return asdict(result)
        except Exception as e:
            raise HTTPException(500, detail=str(e))
