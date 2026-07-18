from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID

from src.domain.entities.executions.models import ExecutionModel


class ExecutionDAOInterface(ABC):
    @abstractmethod
    async def create(
        self,
        agent_id: str,
        initial_input: Dict[str, Any] | None = None,
    ) -> ExecutionModel:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, id: UUID) -> ExecutionModel | None:
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, id: UUID, status: str) -> ExecutionModel | None:
        raise NotImplementedError

    @abstractmethod
    async def soft_delete(self, execution_id: UUID) -> None:
        raise NotImplementedError
