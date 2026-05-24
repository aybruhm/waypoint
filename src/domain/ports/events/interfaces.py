from abc import ABC, abstractmethod
from typing import Any
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
        filters: list[Any],
        offset: int,
        limit: int,
    ) -> list[EventModel]:
        raise NotImplementedError
