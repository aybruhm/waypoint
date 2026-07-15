from uuid import UUID

from sqlalchemy import select

from src.domain.ports.events.interfaces import EventDAOInterface, EventModel
from src.domain.services.events_schema_registry import EventSchemaRegistry
from src.infrastructure.dbs.postgres.engine import get_db_session
from src.infrastructure.dbs.postgres.events.dbes import EventDBE


class EventDAO(EventDAOInterface):
    def _map_dbe_to_model(self, dbe: EventDBE) -> EventModel:
        raw = {
            "id": dbe.id,
            "execution_id": dbe.execution_id,
            "step_number": dbe.step_number,
            "step_name": dbe.step_name,
            "input": dbe.input,
            "output": dbe.output,
            "status": dbe.status,
            "side_effects": dbe.side_effects,
            "cached": dbe.cached,
            "error": dbe.error,
            "duration_ms": dbe.duration_ms,
            "schema_version": getattr(dbe, "schema_version", None) or 1,
            "created_at": dbe.created_at.isoformat(),
        }
        return EventSchemaRegistry.deserialize(raw=raw)

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

    async def insert_batch(self, events: list[EventModel]) -> None:
        async with get_db_session() as session:
            dbes = [
                EventDBE(
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
                for event in events
            ]

            session.add_all(dbes)
            await session.commit()

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
