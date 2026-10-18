import asyncio

from src.domain.entities.events.models import EventModel
from src.domain.ports.events.interfaces import EventDAOInterface
from src.infrastructure.config import logger


class BatchEventWriter:
    """
    Buffers the event model objects in memory and flushes them to the DB in bulk.

    Two flush triggers:
        1. Buffer reaches batch_size (immediate flush)
        2. flush_interval_ms timer fires (periodic flush)

    On crash, the buffer is lost but the checkpoint mechanism already covers recovery. Any un-flushed events will be re-executed on replay.
    """

    def __init__(
        self,
        event_dao: EventDAOInterface,
        flush_interval_ms: int = 10,
        batch_size: int = 100,
    ):
        self._dao = event_dao
        self._flush_interval_ms = flush_interval_ms
        self._batch_size = batch_size
        self._buffer: list[EventModel] = []
        self._lock = asyncio.Lock()

    async def _flush_locked(self) -> None:
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer.clear()

        try:
            await self._dao.insert_batch(events=batch)
        except Exception as e:
            # Re-queue so events aren't silently dropped whilst letting the caller sees the error.
            self._buffer = batch + self._buffer
            logger.error(
                f"BatchEventWritter flush failed, {len(batch)} events re-queued: {str(e)}"
            )
            raise

    async def add_event(self, event: EventModel) -> None:
        async with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self._batch_size:
                await self._flush_locked()

    async def start_periodic_flush(self) -> None:
        """Run as a background task for the lifetime of an execution."""

        while True:
            await asyncio.sleep(self._flush_interval_ms / 1000.0)
            async with self._lock:
                await self._flush_locked()

    async def shutdown(self) -> None:
        """Flush any remaining events before the execution context is torn down."""

        async with self._lock:
            await self._flush_locked()
        logger.info("BatchEventWriter shut down cleanly.")
