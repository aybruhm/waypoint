import re
from typing import Any
from uuid import UUID

from src.domain.ports.deletion_requests.interfaces import DeletionRequestDAOInterface
from src.domain.ports.events.interfaces import EventDAOInterface
from src.domain.ports.executions.interfaces import ExecutionDAOInterface
from src.domain.services.audit_log_service import AuditLogService


class DeletionService:
    def __init__(
        self,
        event_dao: EventDAOInterface,
        execution_dao: ExecutionDAOInterface,
        deletion_request_dao: DeletionRequestDAOInterface,
        audit_log_service: AuditLogService,
    ):
        self._events = event_dao
        self._executions = execution_dao
        self._requests = deletion_request_dao
        self._audit = audit_log_service

    def _mask_pii(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively replace known PII patterns with redacted placeholders.
        """

        masked: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                # email:  user@example.com  →  u***@example.com
                value = re.sub(
                    r"[\w\.-]+@[\w\.-]+",
                    lambda m: m.group(0)[0] + "***@" + m.group(0).split("@")[1],
                    value,
                )
                # phone:  555-1234  →  ***-****
                value = re.sub(r"\b\d{3}-\d{4}\b", "***-****", value)
                # SSN:    123-45-6789  →  ***-**-****
                value = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****", value)
            elif isinstance(value, dict):
                value = self._mask_pii(value)
            elif isinstance(value, list):
                value = [self._mask_pii(i) if isinstance(i, dict) else i for i in value]
            masked[key] = value
        return masked

    async def request_deletion(
        self,
        execution_id: UUID,
        reason: str = "user_request",
    ) -> UUID:
        """
        Create a pending deletion request and return its ID.
        """

        request_id = await self._requests.create(
            execution_id=execution_id,
            reason=reason,
        )
        await self._audit.log(
            action="deletion_requested",
            execution_id=execution_id,
            details={"reason": reason},
        )
        return request_id

    async def execute_deletion(self, execution_id: UUID) -> None:
        """
        Run by background worker. Redacts PII, soft-deletes the execution,
        and marks the deletion request complete.
        """
        # Step 1: mask PII in every event for this execution
        events = await self._events.query(
            execution_id=execution_id, offset=0, limit=10_000
        )
        for event in events:
            await self._events.update_pii_fields(
                event_id=event.id,
                input=self._mask_pii(event.input),
                output=self._mask_pii(event.output),
            )

        # Step 2: soft-delete the execution row
        await self._executions.soft_delete(execution_id=execution_id)

        # Step 3: mark deletion complete
        await self._requests.mark_completed(execution_id=execution_id)

        # Step 4: audit
        await self._audit.log(action="execution_deleted", execution_id=execution_id)
