from typing import Any, Dict

from src.domain.entities.executions.models import ExecutionModel
from src.domain.ports.executions.interfaces import ExecutionDAOInterface


class ExecutionService:
    def __init__(self, execution_dao: ExecutionDAOInterface):
        self.execution_dao = execution_dao

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
