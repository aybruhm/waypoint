import traceback
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.exceptions import HTTPException

from src.application.models import (
    CreateExecutionRequest,
    CreateExecutionResponse,
    ExecutionHistoryResponse,
    ExecutionStatusResponse,
    ExecutionStep,
    ReplayFromStepRequest,
)
from src.domain.exceptions import CheckpointNotFoundError
from src.domain.services.events_service import EventService
from src.domain.services.executions_service import ExecutionService
from src.domain.services.replay_engine import ReplayEngine
from src.infrastructure.workers.celery_app import celery_app


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
            "/{execution_id}/status",
            endpoint=self.get_execution_status,
            methods=["GET"],
            response_model=ExecutionStatusResponse,
        )
        self.router.add_api_route(
            "/{execution_id}/cancel",
            endpoint=self.cancel_execution,
            methods=["POST"],
            response_model=ExecutionStatusResponse,
        )
        self.router.add_api_route(
            "/{execution_id}/replay",
            endpoint=self.replay_from_step,
            methods=["POST"],
            response_model=dict,
        )

    # Queries -----------------------------

    async def get_execution_status(
        self,
        request: Request,
        execution_id: UUID,
    ) -> ExecutionStatusResponse:
        execution = await self.executions_service.get_by_id(execution_id=execution_id)
        if not execution:
            raise HTTPException(
                status_code=404, detail=f"Execution with ID {execution_id} not found"
            )

        execution_status = ExecutionStatusResponse(
            execution_id=execution.id,
            status=execution.status,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )
        return execution_status

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

    # Mutations ----------------------------

    async def create_execution(
        self,
        request: Request,
        body: CreateExecutionRequest,
    ) -> ExecutionStatusResponse:
        try:
            initial_input = body.initial_input or {}
            execution = await self.executions_service.create_execution(
                agent_id=body.agent_id,
                initial_input=initial_input,
            )
            return ExecutionStatusResponse(
                execution_id=execution.id,
                status=execution.status,
            )
        except Exception as e:
            traceback.print_exc()
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

    async def cancel_execution(
        self,
        request: Request,
        execution_id: UUID,
    ) -> ExecutionStatusResponse:
        execution = await self.executions_service.get_by_id(execution_id=execution_id)
        if not execution:
            raise HTTPException(
                status_code=404, detail=f"Execution with ID {execution_id} not found"
            )
        if execution.status not in ("queued", "running"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel an execution in status '{execution.status}'",
            )

        celery_app.control.revoke(str(execution_id), terminate=True)
        updated = await self.executions_service.update_status(execution_id, "cancelled")
        if not updated:
            raise HTTPException(
                status_code=404, detail=f"Execution with ID {execution_id} not found"
            )

        return ExecutionStatusResponse(
            execution_id=updated.id, status=str(updated.status)
        )

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
