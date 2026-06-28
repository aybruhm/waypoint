from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.events.models import EventModel


class EventDAOInterface(ABC):
    @abstractmethod
    async def create(self, event: EventModel) -> EventModel:
        raise NotImplementedError

    @abstractmethod
    async def query(
        self,
        execution_id: UUID,
        offset: int,
        limit: int,
        up_to_step: int | None = None,
    ) -> list[EventModel]:
        raise NotImplementedError

    @abstractmethod
    async def insert_batch(self, events: list[EventModel]) -> None:
        raise NotImplementedError
