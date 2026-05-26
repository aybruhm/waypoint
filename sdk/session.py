from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from .models import ExecutionResult

if TYPE_CHECKING:
    from .gateway import Waypoint

log = logging.getLogger(f"sdk.{__name__}")


class WaypointSession:
    """
    Scopes a series of step executions to a shared execution_id.

    Can be used as an async context manager:

        ```python
        async with waypoint.session(execution_id) as sess:
            await sess.async_execute("step_a", {...})
            await sess.async_execute("step_b", {...})
        ```
    """

    def __init__(self, gateway: Waypoint, execution_id: UUID) -> None:
        self._gateway = gateway
        self.execution_id = execution_id
        self._results: list[ExecutionResult] = []

    # ── execute ────────────────────────────────────────────────────────────────

    async def async_execute(
        self,
        step_name: str,
        parameters: dict[str, Any],
        *,
        cache: bool = False,
    ) -> ExecutionResult:
        """Execute a step scoped to this session's execution_id."""
        result = await self._gateway.async_execute(
            step_name,
            parameters,
            execution_id=self.execution_id,
            cache=cache,
        )
        self._results.append(result)
        return result

    # ── decorator scoped to this session ────────────────────────────────────────

    def checkpoint(
        self,
        name: str | None = None,
        *,
        cache: bool = False,
    ):
        """Same as Waypoint.checkpoint() but pins execution_id to this session."""
        return self._gateway.checkpoint(name, cache=cache)

    # ── session summary ────────────────────────────────────────────────────────

    @property
    def results(self) -> list[ExecutionResult]:
        return list(self._results)

    @property
    def step_count(self) -> int:
        return len(self._results)

    # ── async context manager ──────────────────────────────────────────────────

    async def __aenter__(self) -> WaypointSession:
        await self._gateway.resume(self.execution_id)
        return self

    async def __aexit__(self, *_: Any) -> None:
        log.info(
            "Session %s completed with %d step(s)",
            self.execution_id,
            len(self._results),
        )

    def __repr__(self) -> str:
        return f"WaypointSession(id={self.execution_id!r}, steps={len(self._results)})"
