from uuid import UUID

from sqlalchemy import select

from src.domain.entities.audit_logs.models import AuditLogModel
from src.domain.ports.audit_logs.interfaces import AuditLogDAOInterface
from src.infrastructure.dbs.postgres.audit_logs.dbes import AuditLogDBE
from src.infrastructure.dbs.postgres.engine import get_db_session


class AuditLogDAO(AuditLogDAOInterface):
    def _map_dbe_to_model(self, dbe: AuditLogDBE) -> AuditLogModel:
        model = AuditLogModel(
            id=dbe.id,  # type: ignore
            execution_id=dbe.execution_id,  # type: ignore
            action=dbe.action,  # type: ignore
            actor_id=dbe.actor_id,  # type: ignore
            details=dbe.details,  # type: ignore
            created_at=dbe.created_at,  # type: ignore
        )
        return model

    async def create(
        self,
        model: AuditLogModel,
    ) -> None:
        async with get_db_session() as session:
            dbe = AuditLogDBE(
                execution_id=model.execution_id,
                action=model.action,
                actor_id=model.actor_id,
                details=model.details,
            )

            session.add(dbe)
            await session.commit()

    async def get_by_execution(
        self,
        execution_id: UUID,
    ) -> list[AuditLogModel]:
        async with get_db_session() as session:
            stmt = select(AuditLogDBE).where(AuditLogDBE.execution_id == execution_id)
            result = await session.execute(stmt)
            dbes = result.scalars()
            models = [self._map_dbe_to_model(dbe=dbe) for dbe in dbes]
            return models
