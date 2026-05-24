from typing import Literal

EVENT_STATUSES = Literal[
    "pending",
    "started",
    "completed",
    "failed",
]
EXECUTION_STATUSES = Literal[
    "running",
    "completed",
    "failed",
]
