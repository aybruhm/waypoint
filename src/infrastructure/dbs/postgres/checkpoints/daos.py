from uuid import UUID

from sqlalchemy import select, update

from src.domain.ports.checkpoints.interfaces import (
    CheckpointDAOInterface,
    CheckpointModel,
)
from src.infrastructure.dbs.postgres.checkpoints.dbes import CheckpointDBE
from src.infrastructure.dbs.postgres.engine import get_db_session


class CheckpointDAO(CheckpointDAOInterface):
    def _map_dbe_to_model(self, dbe: CheckpointDBE) -> CheckpointModel:
        return CheckpointModel(
            id=dbe.id,  # type: ignore
            execution_id=dbe.agent_id,  # type: ignore
            step_number=dbe.step_number,  # type: ignore
            completed_at=dbe.completed_at,  # type: ignore
            state_hash=dbe.state_hash,  # type: ignore
            created_at=dbe.created_at,  # type: ignore
        )

    async def upsert(self, checkpoint: CheckpointModel) -> CheckpointModel | None:
        last_checkpoint = await self.get_last(execution_id=checkpoint.execution_id)
        async with get_db_session() as session:
            if last_checkpoint is not None:
                stmt = (
                    update(CheckpointDBE)
                    .where(CheckpointDBE.execution_id == checkpoint.execution_id)
                    .values(
                        step_number=checkpoint.step_number,
                        completed_at=checkpoint.completed_at,
                        state_hash=checkpoint.state_hash,
                    )
                )
                await session.execute(stmt)
            else:
                checkpoint_dbe = CheckpointDBE(
                    execution_id=checkpoint.execution_id,
                    step_number=checkpoint.step_number,
                    completed_at=checkpoint.completed_at,
                    state_hash=checkpoint.state_hash,
                )
                session.add(checkpoint_dbe)

            await session.commit()

        latest_checkpoint = await self.get_last(execution_id=checkpoint.execution_id)
        if not latest_checkpoint:
            return None
        return latest_checkpoint

    async def get_last(self, execution_id: UUID) -> CheckpointModel | None:
        async with get_db_session() as session:
            stmt = (
                select(CheckpointDBE)
                .where(CheckpointDBE.execution_id == execution_id)
                .order_by(CheckpointDBE.step_number.desc())
            )
            result = await session.execute(stmt)
            checkpoint_dbe = result.scalars().first()
            if not checkpoint_dbe:
                return None

            checkpoint_model = self._map_dbe_to_model(dbe=checkpoint_dbe)
            return checkpoint_model
