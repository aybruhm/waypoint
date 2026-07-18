from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.audit_logs.models import AuditLogModel


class AuditLogDAOInterface(ABC):
    @abstractmethod
    async def create(
        self,
        model: AuditLogModel,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_execution(
        self,
        execution_id: UUID,
    ) -> list[AuditLogModel]:
        raise NotImplementedError
