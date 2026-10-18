from abc import ABC, abstractmethod
from uuid import UUID


class DeletionRequestDAOInterface(ABC):
    @abstractmethod
    async def create(
        self,
        execution_id: UUID,
        reason: str,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def mark_completed(
        self,
        execution_id: UUID,
    ) -> None:
        raise NotImplementedError
