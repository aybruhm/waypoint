import traceback

from fastapi import APIRouter, Query, Request
from fastapi.exceptions import HTTPException

from src.application.models import (
    CheckpointResponse,
    CheckpointStateResponse,
    CreateCheckpointRequest,
    LoadStateFromCheckpointRequest,
)
from src.domain.services.checkpoints_service import CheckpointService
from src.domain.services.events_service import EventService
from src.domain.services.types import EventCreateData


class CheckpointAPIRouter:
    def __init__(
        self, checkpoints_service: CheckpointService, events_service: EventService
    ) -> None:
        self.checkpoints_service = checkpoints_service
        self.events_service = events_service

        self.router = APIRouter()

        # Register routes
        self.router.add_api_route(
            "/",
            endpoint=self.create_checkpoint,
            methods=["POST"],
            response_model=CheckpointResponse,
        )
        self.router.add_api_route(
            "/load",
            endpoint=self.load_state_from_checkpoint,
            methods=["POST"],
            response_model=CheckpointStateResponse,
        )

    async def create_checkpoint(
        self, request: Request, checkpoint_data: CreateCheckpointRequest
    ):
        try:
            await self.events_service.log_event(
                execution_id=checkpoint_data.execution_id,
                step_number=checkpoint_data.step_number,
                event_data=EventCreateData(
                    step_name=checkpoint_data.step_name,
                    status=checkpoint_data.status,
                    input_data=checkpoint_data.input_data,
                    output_data=checkpoint_data.output_data,
                    error=checkpoint_data.error,
                    duration_ms=checkpoint_data.duration_ms,
                    cached=checkpoint_data.cached,
                ),
            )

            checkpoint = await self.checkpoints_service.create_checkpoint(
                execution_id=checkpoint_data.execution_id,
                step_number=checkpoint_data.step_number,
                state=checkpoint_data.state,
            )
            return CheckpointResponse(
                id=checkpoint.id,
                execution_id=checkpoint.execution_id,
                step_number=checkpoint.step_number,
                completed_at=checkpoint.completed_at,
                state_hash=checkpoint.state_hash,
                created_at=checkpoint.created_at,
            )
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, detail=str(e))

    async def load_state_from_checkpoint(
        self,
        request: Request,
        request_data: LoadStateFromCheckpointRequest,
        offset: int = Query(0),
        limit: int = Query(100),
    ):
        try:
            events = await self.events_service.list_events(
                execution_id=request_data.execution_id,
                up_to_step=request_data.step_number,
                offset=offset,
                limit=limit,
            )
            checkpoint_state = self.events_service.reconstruct_state(events=events)
            return checkpoint_state
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, detail=str(e))
