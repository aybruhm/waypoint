from uuid import UUID

from sqlalchemy import update

from src.domain.ports.deletion_requests.interfaces import DeletionRequestDAOInterface
from src.infrastructure.dbs.postgres.deletion_requests.dbes import DeletionRequestDBE
from src.infrastructure.dbs.postgres.engine import get_db_session


class DeletionRequestDAO(DeletionRequestDAOInterface):
    async def create(
        self,
        execution_id: UUID,
        reason: str,
    ) -> UUID:
        async with get_db_session() as session:
            dbe = DeletionRequestDBE(
                execution_id=execution_id,
                reason=reason,
            )

            session.add(dbe)
            await session.commit()
            return dbe.id  # type: ignore

    async def mark_completed(
        self,
        execution_id: UUID,
    ) -> None:
        async with get_db_session() as session:
            stmt = (
                update(DeletionRequestDBE)
                .where(DeletionRequestDBE.execution_id)
                .values(status="completed")
            )

            await session.execute(stmt)
            await session.commit()
