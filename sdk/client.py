import asyncio
import logging
from typing import Any
from uuid import UUID

import httpx

from .exceptions import (
    CheckpointNotFoundError,
    ExecutionNotFoundError,
    GatewayError,
    WaypointClientError,
)
from .models import (
    CheckpointResponse,
    ExecutionHistory,
    ExecutionInfo,
    ExecutionStep,
    ReplayState,
    ResumeState,
)

log = logging.getLogger(f"sdk.{__name__}")


class WaypointClient:
    """
    Low-level HTTP client for the Waypoint API.

    Manages reusable httpx clients (sync and async) with lazy initialisation, thread-safety locks, and explicit close/aclose lifecycle.
    """

    def __init__(
        self,
        *,
        base_url: str,
        workflow_id: str,
        timeout: float = 30.0,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.workflow_id = workflow_id
        self.timeout = timeout
        self.api_key = api_key

        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

        self._sync_lock = asyncio.Lock()
        self._async_lock = asyncio.Lock()

    # ── low-level HTTP helpers ──────────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        if self.api_key:
            return {"X-WAYPOINT-API-KEY": f"{self.api_key}"}
        return {}

    def _http(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                headers=self._auth_headers(),
                timeout=self.timeout,
                trust_env=False,
            )
        return self._sync_client

    async def _ahttp(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._auth_headers(),
                timeout=self.timeout,
                trust_env=False,
            )
        return self._async_client

    def close(self) -> None:
        if self._sync_client:
            self._sync_client.close()

    async def aclose(self) -> None:
        if self._async_client:
            await self._async_client.aclose()

    # ── request dispatch ────────────────────────────────────────────────────────

    @staticmethod
    def _build_path(
        execution_id: UUID,
        resource: str,
        *,
        include_load: bool = False,
    ) -> str:
        if resource == "create_execution":
            return "/executions/"
        if resource == "checkpoint":
            return "/checkpoints/"
        if resource == "checkpoint_load":
            return "/checkpoints/load"
        if resource == "history":
            return f"/executions/{execution_id}/history"
        if resource == "resume":
            return f"/executions/{execution_id}/resume"
        if resource == "replay":
            return f"/executions/{execution_id}/replay"
        if resource == "delete":
            return f"/executions/{execution_id}"
        msg = f"Unknown resource: {resource}"
        raise ValueError(msg)

    async def _arequest(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        try:
            http = await self._ahttp()
            resp = await http.request(
                method,
                path,
                json=json_body,
                params=params,
            )
            body: dict[str, Any] = resp.json()
            if not resp.is_success:
                detail = body.get("detail", str(resp.reason_phrase))
                if resp.status_code == 404:
                    msg = detail if isinstance(detail, str) else str(detail)
                    if "checkpoint" in msg.lower():
                        raise CheckpointNotFoundError(msg)
                    raise ExecutionNotFoundError(msg)
                raise WaypointClientError(resp.status_code, detail)
            return body
        except httpx.ConnectError as exc:
            raise GatewayError(self.base_url, exc) from exc
        except httpx.TimeoutException as exc:
            raise GatewayError(self.base_url, exc) from exc

    # ── API methods ─────────────────────────────────────────────────────────────

    async def create_execution(
        self,
        workflow_id: str,
        initial_input: dict[str, Any] | None = None,
    ) -> ExecutionInfo:
        body = await self._arequest(
            "POST",
            "/executions/",
            json_body={
                "workflow_id": workflow_id,
                "initial_input": initial_input,
            },
        )
        return ExecutionInfo(
            id=UUID(body["id"]) if isinstance(body["id"], str) else body["id"],
            workflow_id=body["workflow_id"],
            status=body["status"],
            started_at=body["started_at"],
            initial_input=body.get("initial_input"),
            created_at=body.get("created_at"),
        )

    async def create_checkpoint(
        self,
        execution_id: UUID,
        step_number: int,
        step_name: str,
        state: dict[str, Any],
        *,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        status: str = "completed",
        duration_ms: int | None = None,
        error: dict[str, Any] | None = None,
        cached: bool = False,
    ) -> CheckpointResponse:
        body = await self._arequest(
            "POST",
            "/checkpoints/",
            json_body={
                "execution_id": str(execution_id),
                "step_number": step_number,
                "step_name": step_name,
                "state": state,
                "input_data": input_data or {},
                "output_data": output_data,
                "status": status,
                "duration_ms": duration_ms,
                "error": error,
                "cached": cached,
            },
        )
        return CheckpointResponse(
            id=UUID(body["id"]) if isinstance(body["id"], str) else body["id"],
            execution_id=UUID(body["execution_id"])
            if isinstance(body["execution_id"], str)
            else body["execution_id"],
            step_number=body["step_number"],
            completed_at=body["completed_at"],
            state_hash=body.get("state_hash"),
            created_at=body.get("created_at"),
        )

    async def resume_execution(self, execution_id: UUID) -> ResumeState:
        body = await self._arequest(
            "POST",
            f"/executions/{execution_id}/resume",
        )
        return ResumeState(
            execution_id=UUID(body["execution_id"])
            if isinstance(body["execution_id"], str)
            else body["execution_id"],
            checkpoint_step=body.get("checkpoint_step", 0),
            reconstructed_state=body.get("reconstructed_state", {}),
            state_hash=body.get("state_hash"),
            ready_to_resume=body.get("ready_to_resume", True),
        )

    async def replay_from_step(
        self,
        execution_id: UUID,
        step_number: int,
    ) -> ReplayState:
        body = await self._arequest(
            "POST",
            f"/executions/{execution_id}/replay",
            json_body={"step_number": step_number},
        )
        return ReplayState(
            execution_id=UUID(body["execution_id"])
            if isinstance(body["execution_id"], str)
            else body["execution_id"],
            replay_from_step=body.get("replay_from_step", step_number),
            reconstructed_state=body.get("reconstructed_state", {}),
            ready_to_resume=body.get("ready_to_resume", True),
        )

    async def get_execution_history(self, execution_id: UUID) -> ExecutionHistory:
        body = await self._arequest("GET", f"/executions/{execution_id}/history")
        steps = [ExecutionStep(**s) for s in body.get("steps", [])]
        return ExecutionHistory(
            execution_id=UUID(body["execution_id"])
            if isinstance(body["execution_id"], str)
            else body["execution_id"],
            workflow_id=body["workflow_id"],
            status=body["status"],
            started_at=body["started_at"],
            completed_at=body.get("completed_at"),
            steps=steps,
        )
