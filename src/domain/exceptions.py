class WaypointError(Exception):
    """Base exception for Waypoint."""

    pass


class CheckpointNotFoundError(WaypointError):
    """Raised when no checkpoint exists for an execution."""

    pass


class ExecutionNotFoundError(WaypointError):
    """Raised when execution metadata cannot be found."""

    pass


class ReplayFailedError(WaypointError):
    """Raised when replay logic encounters an error."""

    pass


class StateReconstructionError(WaypointError):
    """Raised when state cannot be reliably reconstructed from events."""

    pass
