from uuid import UUID

from sqlalchemy import select

from src.domain.ports.events.interfaces import EventDAOInterface, EventModel
from src.infrastructure.dbs.postgres.engine import get_db_session
from src.infrastructure.dbs.postgres.events.dbes import EventDBE


class EventDAO(EventDAOInterface):
    def _map_dbe_to_model(self, dbe: EventDBE) -> EventModel:
        return EventModel(
            id=UUID(str(dbe.id)),
            execution_id=UUID(str(dbe.execution_id)),
            step_number=dbe.step_number,  # type: ignore
            step_name=dbe.step_name,  # type: ignore
            input=dbe.input,  # type: ignore
            output=dbe.output,  # type: ignore
            status=dbe.status,  # type: ignore
            side_effects=dbe.side_effects,  # type: ignore
            cached=dbe.cached,  # type: ignore
            error=dbe.error,  # type: ignore
            duration_ms=dbe.duration_ms,  # type: ignore
            created_at=dbe.created_at,  # type: ignore
        )

    async def create(self, event: EventModel) -> EventModel:
        async with get_db_session() as session:
            event_dbe = EventDBE(
                execution_id=event.execution_id,
                step_number=event.step_number,
                step_name=event.step_name,
                input=event.input,
                output=event.output,
                side_effects=event.side_effects,
                cached=event.cached,
                status=event.status,
                error=event.error,
                duration_ms=event.duration_ms,
            )

            session.add(event_dbe)
            await session.commit()

            event_model = self._map_dbe_to_model(dbe=event_dbe)
            return event_model

    async def query(
        self,
        execution_id: UUID,
        offset: int,
        limit: int,
        up_to_step: int | None = None,
    ) -> list[EventModel]:
        async with get_db_session() as session:
            stmt = (
                select(EventDBE)
                .where(EventDBE.execution_id == execution_id)
                .order_by(EventDBE.step_number.asc())
            )
            if up_to_step is not None:
                stmt = stmt.where(EventDBE.step_number <= up_to_step)

            result = await session.execute(stmt)
            events_dbes = result.scalars().all()
            events_models = [
                self._map_dbe_to_model(dbe=event_dbe) for event_dbe in events_dbes
            ]
            return events_models
