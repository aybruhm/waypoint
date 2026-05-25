from uuid import UUID

from src.domain.exceptions import CheckpointNotFoundError
from src.domain.services.checkpoints_service import CheckpointService
from src.domain.services.events_service import EventService
from src.domain.services.types import CheckpointState, ReplayState


class ReplayEngine:
    """Deterministic execution replay from checkpoints"""

    def __init__(
        self,
        events_service: EventService,
        checkpoints_service: CheckpointService,
    ):
        self.events_service = events_service
        self.checkpoints_service = checkpoints_service

    async def replay_from_checkpoint(
        self,
        execution_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> CheckpointState:
        """
        Resume the execution from its last checkpoint.

        Workflow:
            1. Load checkpoint for the execution.
            2. Reconstruct state from events up to the last checkpoint step.
            3. Return reconstructed state + last checkpoint step number.
        """

        checkpoint = await self.checkpoints_service.get_last_checkpoint(
            execution_id=execution_id
        )
        if not checkpoint or not checkpoint.state_hash:
            raise CheckpointNotFoundError(
                f"No checkpoint found for execution {execution_id}"
            )

        # Load events up to last checkpoint
        events = await self.events_service.list_events(
            execution_id=execution_id,
            checkpoint_step_number=checkpoint.step_number,
            offset=offset,
            limit=limit,
        )

        # Reconstruct state
        state = self.events_service.reconstruct_state(events=events)
        checkpoint_state = CheckpointState(
            execution_id=execution_id,
            checkpoint_step=checkpoint.step_number,
            reconstructed_state=state,
            state_hash=checkpoint.state_hash,
            ready_to_resume=True,
        )
        return checkpoint_state

    async def replay_from_step(
        self,
        execution_id: UUID,
        step_number: int,
        offset: int = 0,
        limit: int = 100,
    ) -> ReplayState:
        """
        Replay the execution from a specific step (for testing/debugging).

        This will allow re-running from an arbitrary step without waiting for crash.
        """

        events = await self.events_service.list_events(
            execution_id=execution_id,
            checkpoint_step_number=step_number,
            offset=offset,
            limit=limit,
        )

        # Reconstruct state
        state = self.events_service.reconstruct_state(events=events)
        replay_state = ReplayState(
            execution_id=execution_id,
            replay_from_state=step_number,
            reconstructed_state=state,
            ready_to_resume=True,
        )
        return replay_state
