import hashlib
import json
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from uuid_utils import uuid7

from src.domain.entities.checkpoints.models import CheckpointModel
from src.domain.exceptions import CheckpointNotFoundError
from src.domain.ports.checkpoints.interfaces import CheckpointDAOInterface


class CheckpointService:
    def __init__(self, checkpoint_dao: CheckpointDAOInterface):
        self.checkpoint_dao = checkpoint_dao

    def _construct_state_hash(self, state: Dict[str, Any]):
        state_hash = hashlib.sha256(
            json.dumps(
                state,
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        return state_hash

    def _map_create_data_to_model(
        self,
        execution_id: UUID,
        step_number: int,
        state_hash: str,
    ) -> CheckpointModel:
        return CheckpointModel(
            id=UUID(str(uuid7())),
            execution_id=UUID(str(execution_id)),
            step_number=step_number,
            completed_at=datetime.now(),
            state_hash=state_hash,
        )

    async def create_checkpoint(
        self,
        execution_id: UUID,
        step_number: int,
        state: Dict[str, Any],
    ) -> CheckpointModel:
        state_hash = self._construct_state_hash(state=state)
        checkpoint_ = self._map_create_data_to_model(
            execution_id=execution_id,
            step_number=step_number,
            state_hash=state_hash,
        )
        checkpoint = await self.checkpoint_dao.upsert(checkpoint=checkpoint_)
        if not checkpoint:
            raise CheckpointNotFoundError(
                f"No checkpoint found for execution {execution_id}"
            )
        return checkpoint

    async def get_last_checkpoint(self, execution_id: UUID):
        checkpoint = await self.checkpoint_dao.get_last(execution_id=execution_id)
        if not checkpoint:
            raise CheckpointNotFoundError(
                f"No checkpoint found for execution {execution_id}"
            )
        return checkpoint
