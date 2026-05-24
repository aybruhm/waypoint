from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.checkpoints.models import CheckpointModel


class CheckpointDAOInterface(ABC):
    @abstractmethod
    async def upsert(self, checkpoint: CheckpointModel) -> CheckpointModel | None:
        raise NotImplementedError

    @abstractmethod
    async def get_last(self, execution_id: UUID) -> CheckpointModel | None:
        raise NotImplementedError
