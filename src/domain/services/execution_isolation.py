from uuid import UUID

from src.domain.services.batch_event_writer import BatchEventWriter
from src.domain.services.events_service import EventService
from src.infrastructure.dbs.postgres.events.daos import EventDAO


class ExecutionIsolation:
    """
    Produces a self-contained (execution_id-scoped) EventService + BatchEventWriter.
    """

    @staticmethod
    async def build_context(
        execution_id: UUID,
    ) -> tuple[EventService, BatchEventWriter]:
        event_dao = EventDAO()
        batch_writer = BatchEventWriter(event_dao=event_dao)
        events_service = EventService(
            event_dao=event_dao,
            batch_writer=batch_writer,
        )
        return events_service, batch_writer
