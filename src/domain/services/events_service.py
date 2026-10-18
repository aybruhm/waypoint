from uuid import UUID

from uuid_utils import uuid7

from src.domain.entities.events.models import EventModel
from src.domain.ports.events.interfaces import EventDAOInterface
from src.domain.services.batch_event_writer import BatchEventWriter
from src.domain.services.types import ConstructedState, EventCreateData


class EventService:
    def __init__(
        self,
        event_dao: EventDAOInterface,
        batch_writer: BatchEventWriter | None = None,
    ):
        self.event_dao = event_dao
        self._batch_writer = batch_writer

    def _map_create_data_to_model(
        self,
        execution_id: UUID,
        step_number: int,
        create_data: EventCreateData,
    ) -> EventModel:
        return EventModel(
            id=UUID(str(uuid7())),
            execution_id=UUID(str(execution_id)),
            step_number=step_number,
            step_name=create_data.step_name,
            input=create_data.input_data,
            output=create_data.output_data if create_data.output_data else {},
            side_effects=create_data.side_effects,
            cached=create_data.cached,
            status=create_data.status,  # type: ignore[assignment]
            error=create_data.error,
            duration_ms=create_data.duration_ms,
        )

    def reconstruct_state(self, events: list[EventModel]) -> ConstructedState:
        state: ConstructedState = {}
        for event in events:
            if event.status == "completed" and event.output:
                state[event.step_name] = event.output
        return state

    async def log_event(
        self,
        execution_id: UUID,
        step_number: int,
        event_data: EventCreateData,
    ) -> EventModel:
        event = self._map_create_data_to_model(
            execution_id=execution_id,
            step_number=step_number,
            create_data=event_data,
        )
        if self._batch_writer:
            # Non-blocking: event is queued in memory, and flushed in background.
            await self._batch_writer.add_event(event=event)
            return event  # optimistic return; persistence is async

        # Fallback: direct single-rwo write (backward-compatible behaviour)
        return await self.event_dao.create(event=event)

    async def list_events(
        self,
        execution_id: UUID,
        up_to_step: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[EventModel]:
        events = await self.event_dao.query(
            execution_id=execution_id,
            up_to_step=up_to_step,
            offset=offset,
            limit=limit,
        )
        return events
