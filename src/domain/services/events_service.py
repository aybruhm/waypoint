from uuid import UUID

from uuid_utils import uuid7

from src.domain.entities.events.models import EventModel
from src.domain.ports.events.interfaces import EventDAOInterface
from src.domain.services.types import ConstructedState, EventCreateData


class EventService:
    def __init__(self, event_dao: EventDAOInterface):
        self.event_dao = event_dao

    def _map_create_data_to_model(
        self,
        execution_id: UUID,
        step_number: int,
        create_data: EventCreateData,
    ) -> EventModel:
        return EventModel(
            id=uuid7(),  # type: ignore[assignment]
            execution_id=execution_id,
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
        state: ConstructedState = {}  # type: ignore[assignment]
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
        _event = self._map_create_data_to_model(
            execution_id=execution_id,
            step_number=step_number,
            create_data=event_data,
        )
        event = await self.event_dao.create(event=_event)
        return event

    async def list_events(
        self,
        execution_id: UUID,
        up_to_step: int | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[EventModel]:
        filters = []
        if up_to_step is not None:
            filters = [
                EventModel.step_number <= up_to_step,
            ]

        events = await self.event_dao.query(
            execution_id=execution_id,
            filters=filters,
            offset=offset,
            limit=limit,
        )
        return events
