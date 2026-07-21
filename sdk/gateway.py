from __future__ import annotations

import contextvars
import functools
import inspect
import json
import logging
import time
import traceback
import uuid
from typing import Any, Callable, TypeVar
from uuid import UUID

from .client import WaypointClient
from .exceptions import WaypointError
from .models import ExecutionResult, ResumeState
from .session import WaypointSession

log = logging.getLogger(f"sdk.{__name__}")
F = TypeVar("F", bound=Callable[..., Any])

_WAYPOINT_ATTR = "_waypoint_checkpoint"

# Module-level active Waypoint for the standalone @checkpoint decorator.
_current_waypoint: contextvars.ContextVar[Waypoint | None] = contextvars.ContextVar(
    "_current_waypoint", default=None
)


class Waypoint:
    """
    Waypoint is the single entry point for workflow execution recovery.

    Usage patterns
    ──────────────
    1. Decorator (recommended):

        ```python
        waypoint = Waypoint(base_url=..., workflow_id=...)
        await waypoint.resume(execution_id)

        @waypoint.checkpoint("load_query")
        async def load_query(query: str) -> dict:
            return {"query": query}

        result = await load_query(query="hello")
        ```

    2. Standalone decorator (no instance reference needed):

        ```python
        waypoint = Waypoint(base_url=..., workflow_id=...).use()
        await waypoint.resume(execution_id)

        @checkpoint("load_query")
        async def load_query(query: str) -> dict:
            return {"query": query}
        ```

    3. Direct execute:

        ```python
        result = await waypoint.async_execute("load_query", {"query": "hello"})
        ```

    4. Session context manager:

        ```python
        async with waypoint.session(execution_id) as sess:
            await sess.async_execute("load_query", {"query": "hello"})
        ```
    """

    def __init__(
        self,
        *,
        base_url: str,
        workflow_id: str,
        timeout: float = 30.0,
        api_key: str | None = None,
    ) -> None:
        self._client = WaypointClient(
            base_url=base_url,
            workflow_id=workflow_id,
            timeout=timeout,
            api_key=api_key,
        )
        self._execution_id: UUID | None = None
        self._step_number: int = 0
        self._state: dict[str, Any] = {}
        self._initialized: bool = False

    def use(self) -> Waypoint:
        """
        Register this instance as the active Waypoint for the standalone ``@checkpoint`` decorator imported from ``sdk``.
        """

        _current_waypoint.set(self)
        return self

    # ── lifecycle ────────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ── state accessors ──────────────────────────────────────────────────────────

    @property
    def execution_id(self) -> UUID | None:
        return self._execution_id

    @execution_id.setter
    def execution_id(self, value: UUID) -> None:
        self._execution_id = value

    def get_state(self) -> dict[str, Any]:
        return dict(self._state)

    def get_step_number(self) -> int:
        return self._step_number

    # ── create ────────────────────────────────────────────────────────────────────

    async def create(
        self,
        initial_input: dict[str, Any] | None = None,
    ) -> UUID:
        """Create a new execution and set it as the active execution."""

        info = await self._client.create_execution(
            workflow_id=self._client.workflow_id,
            initial_input=initial_input,
        )
        self._execution_id = info.id
        self._step_number = 0
        self._state = {}
        self._initialized = True
        log.info("Created execution %s for workflow %s", info.id, info.workflow_id)
        return info.id

    # ── resume ───────────────────────────────────────────────────────────────────

    async def resume(self, execution_id: UUID) -> ResumeState:
        """Resume an execution from its last checkpoint, restoring local state."""

        self._execution_id = execution_id
        result = await self._client.resume_execution(execution_id)
        self._step_number = result.checkpoint_step
        if result.reconstructed_state:
            self._state.update(result.reconstructed_state)

        self._initialized = True
        log.info(
            "Resumed execution %s at step %d (state keys: %s)",
            execution_id,
            self._step_number,
            list(self._state.keys()),
        )
        return result

    # ── step execution ──────────────────────────────────────────────────────────

    async def async_execute(
        self,
        step_name: str,
        parameters: dict[str, Any],
        *,
        execution_id: UUID | None = None,
        cache: bool = False,
    ) -> ExecutionResult:
        """
        Execute a single step, recording a checkpoint on completion.

        When *cache=True* and the step output is already present in the
        reconstructed state, the cached value is returned and no user
        function is called.

        Args:
            step_name  (str):  unique name for this step
            parameters (dict):  input data for the step
            execution_id (UUID | None): override the instance execution_id
            cache (bool): return cached output if available

        Returns:
            ExecutionResult with the step output or error details.
        """

        eid = execution_id or self._execution_id
        if eid is None:
            raise ValueError(
                "execution_id is required — pass one to async_execute, "
                "set execution_id on the instance, or call resume() first"
            )

        # ── extract input data (without __callable__) ─────────────────────────
        input_data = (
            {k: v for k, v in parameters.items() if k != "__callable__"}
            if isinstance(parameters, dict)
            else {}
        )

        # ── cache hit ──────────────────────────────────────────────────────────
        if cache and step_name in self._state:
            output = self._state[step_name]
            self._step_number += 1
            await self._client.create_checkpoint(
                eid,
                self._step_number,
                step_name,
                self._state,
                input_data=input_data,
                output_data=output,
                cached=True,
                duration_ms=0,
            )
            return ExecutionResult(
                execution_id=eid,
                step_number=self._step_number,
                step_name=step_name,
                output=output,
                cached=True,
                duration_ms=0,
            )

        # ── execute the user-provided callable ──────────────────────────────────
        start = None
        func = (
            parameters.pop("__callable__", None)
            if isinstance(parameters, dict)
            else None
        )
        if func is None:
            raise RuntimeError("No callable provided — expected an async function")
        if not inspect.iscoroutinefunction(func):
            raise RuntimeError(f"{func.__name__} must be an async function")

        if func is not None and callable(func):
            start = time.time()
            try:
                output = await func(**parameters)  # type: ignore
                json.dumps(output, default=str)
            except Exception as exc:
                duration_ms = int((time.time() - start) * 1000)
                error = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
                self._step_number += 1
                await self._client.create_checkpoint(
                    eid,
                    self._step_number,
                    step_name,
                    self._state,
                    input_data=input_data,
                    error=error,
                    status="failed",
                    duration_ms=duration_ms,
                )
                return ExecutionResult(
                    execution_id=eid,
                    step_number=self._step_number,
                    step_name=step_name,
                    output={"error": error},
                    error=error,
                    cached=False,
                    duration_ms=duration_ms,
                )
        else:
            output = parameters
            if not isinstance(output, dict):
                output = {"result": output}

        duration_ms = int((time.time() - start) * 1000) if start is not None else 0
        self._step_number += 1
        self._state[step_name] = output
        await self._client.create_checkpoint(
            eid,
            self._step_number,
            step_name,
            self._state,
            input_data=input_data,
            output_data=output,
            duration_ms=duration_ms,
        )

        return ExecutionResult(
            execution_id=eid,
            step_number=self._step_number,
            step_name=step_name,
            output=output,
            cached=False,
            duration_ms=duration_ms,
        )

    # ── decorator: @waypoint.checkpoint ─────────────────────────────────────────

    def checkpoint(
        self,
        name: str | None = None,
        *,
        cache: bool = False,
    ) -> Callable[[F], F]:
        """
        Decorator that gates the decorated async function behind a checkpoint.

        Args:
            name (str | None): step name (defaults to ``<module>.<qualname>``)
            cache (bool):  return cached output on replay if available

        Example:

            ```python
            @waypoint.checkpoint("load_query")
            async def load_query(query: str) -> dict:
                return {"query": query, "normalized": query.lower()}
            ```
        """

        def decorator(func: F) -> F:
            resolved_name = name or f"{func.__module__}.{func.__qualname__}"
            sig = inspect.signature(func)

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                params: dict[str, Any] = {}
                try:
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    params = dict(bound.arguments)
                except TypeError:
                    params = kwargs

                params["__callable__"] = func

                result = await self.async_execute(
                    resolved_name,
                    params,
                    cache=cache,
                )
                if result.error:
                    raise WaypointError(str(result.error))
                return result.output

            setattr(wrapper, _WAYPOINT_ATTR, True)
            setattr(wrapper, "_waypoint_step", resolved_name)
            return wrapper  # type: ignore[return-value]

        return decorator

    # ── session context manager ─────────────────────────────────────────────────

    def session(self, execution_id: UUID | None = None) -> WaypointSession:
        """
        Return a WaypointSession that scopes all calls to a single execution_id.

        Usage:
            ```python
            async with waypoint.session(execution_id) as sess:
                await sess.async_execute("step_a", {...})
                await sess.async_execute("step_b", {...})
            ```
        """
        return WaypointSession(self, execution_id or uuid.uuid4())


# ── standalone decorator ─────────────────────────────────────────────────────


def checkpoint(
    name: str | None = None,
    *,
    cache: bool = False,
) -> Callable[[F], F]:
    """
    Standalone ``@checkpoint`` decorator.

    Requires an active ``Waypoint`` instance registered via ``waypoint.use()``.

    Example:
        ```python
        from sdk import Waypoint, checkpoint

        waypoint = Waypoint(base_url=..., workflow_id=...).use()
        await waypoint.resume(execution_id)

        @checkpoint("load_query")
        async def load_query(query: str) -> dict:
        ```
    """
    wp = _current_waypoint.get()
    if wp is None:
        raise RuntimeError(
            "No active Waypoint instance. Call Waypoint(...).use() before using @checkpoint."
        )
    return wp.checkpoint(name=name, cache=cache)
