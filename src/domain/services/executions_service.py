from typing import Any, Dict
from uuid import UUID

from src.domain.entities.executions.models import ExecutionModel
from src.domain.ports.executions.interfaces import ExecutionDAOInterface


class ExecutionService:
    def __init__(self, execution_dao: ExecutionDAOInterface):
        self.execution_dao = execution_dao

    # Mutations -----------------
    async def create_execution(
        self,
        agent_id: str,
        initial_input: Dict[str, Any] | None = None,
    ) -> ExecutionModel:
        execution = await self.execution_dao.create(
            agent_id=agent_id,
            initial_input=initial_input,
        )
        return execution

    async def update_status(
        self, execution_id: UUID, status: str
    ) -> ExecutionModel | None:
        execution = await self.execution_dao.update_status(
            id=execution_id,
            status=status,
        )
        return execution

    # Queries ---------------------
    async def get_by_id(self, execution_id: UUID) -> ExecutionModel | None:
        execution = await self.execution_dao.get_by_id(id=execution_id)
        return execution
