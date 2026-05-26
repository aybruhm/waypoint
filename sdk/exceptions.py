class WaypointError(Exception):
    """Base exception for all Waypoint SDK errors."""

    pass


class GatewayError(WaypointError):
    """Raised when the Waypoint API is unreachable and no fail-open policy applies."""

    def __init__(self, gateway_url: str, original: Exception) -> None:
        self.gateway_url = gateway_url
        self.original = original
        super().__init__(f"Waypoint API at {gateway_url!r} unreachable: {original}")


class CheckpointError(WaypointError):
    """Raised when a checkpoint operation fails."""

    pass


class ExecutionNotFoundError(WaypointError):
    """Raised when the execution does not exist on the server."""

    pass


class CheckpointNotFoundError(WaypointError):
    """Raised when no checkpoint exists for an execution."""

    pass


class WaypointClientError(WaypointError):
    """Raised when the API returns an unexpected error status."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class WaypointConnectionError(WaypointError):
    """Raised when the SDK cannot connect to the Waypoint API."""

    pass


class WaypointTimeoutError(WaypointError):
    """Raised when a request to the Waypoint API times out."""

    pass
