from typing import Any
from uuid import UUID

from src.domain.entities.audit_logs.models import AuditLogModel
from src.domain.ports.audit_logs.interfaces import AuditLogDAOInterface


class AuditLogService:
    """
    Append-only audit trail. Every sensitive operation in the system should
    call .log() so there is a durable record of who did what and when.
    """

    def __init__(self, audit_log_dao: AuditLogDAOInterface):
        self._dao = audit_log_dao

    async def log(
        self,
        action: str,
        execution_id: UUID,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self._dao.create(
            model=AuditLogModel(
                execution_id=execution_id,
                action=action,
                actor_id=actor_id or "system",
                details=details or {},
            )
        )

    async def get_trail(self, execution_id: UUID) -> list[AuditLogModel]:
        audit_logs = await self._dao.get_by_execution(execution_id=execution_id)
        return audit_logs
