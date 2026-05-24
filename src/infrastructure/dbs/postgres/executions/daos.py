from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select, update

from src.domain.ports.executions.interfaces import ExecutionDAOInterface, ExecutionModel
from src.infrastructure.dbs.postgres.engine import get_db_session
from src.infrastructure.dbs.postgres.executions.dbes import ExecutionDBE


class ExecutionDAO(ExecutionDAOInterface):
    def _map_dbe_to_model(self, dbe: ExecutionDBE) -> ExecutionModel:
        return ExecutionModel(
            id=dbe.id,  # type: ignore
            agent_id=dbe.agent_id,  # type: ignore
            status=dbe.status,  # type: ignore
            started_at=dbe.started_at,  # type: ignore
            completed_at=dbe.completed_at,  # type: ignore
            initial_input=dbe.initial_input,  # type: ignore
            created_at=dbe.created_at,  # type: ignore
            updated_at=dbe.updated_at,  # type: ignore
        )

    async def create(
        self,
        agent_id: str,
        initial_input: Dict[str, Any] | None = None,
    ) -> ExecutionModel:
        async with get_db_session() as session:
            execution_dbe = ExecutionDBE(
                agent_id=agent_id,
                initial_input=initial_input,
            )

            session.add(execution_dbe)
            await session.commit()

            execution_model = self._map_dbe_to_model(dbe=execution_dbe)
            return execution_model

    async def get_by_id(self, id: UUID) -> ExecutionModel | None:
        async with get_db_session() as session:
            stmt = select(ExecutionDBE).where(ExecutionDBE.id == id)
            result = await session.execute(stmt)
            execution_dbe = result.scalar_one_or_none()
            if not execution_dbe:
                return None

            execution_model = self._map_dbe_to_model(dbe=execution_dbe)
            return execution_model

    async def update_status(self, id: UUID, status: str) -> ExecutionModel | None:
        async with get_db_session() as session:
            stmt = (
                update(ExecutionDBE)
                .where(ExecutionDBE.id == id)
                .values(status=status)
                .returning(ExecutionDBE)
            )
            result = await session.execute(stmt)
            await session.commit()
            execution_dbe = result.scalar_one_or_none()
            if not execution_dbe:
                return None

            execution_model = self._map_dbe_to_model(dbe=execution_dbe)
            return execution_model
