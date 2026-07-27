"""
Simple 3-step agent workflow using the Waypoint SDK.

Prerequisites:
    - Waypoint API running at http://localhost:9654

Usage:
    uv run python -m sdk.examples.simple_agent
"""

import asyncio
from uuid import UUID

from sdk import Waypoint, checkpoint

WORKFLOW_ID = "simple_agent"
API_BASE_URL = "http://localhost:9654/api/v1/"

waypoint = Waypoint(
    base_url=API_BASE_URL,
    workflow_id=WORKFLOW_ID,
).use()


@checkpoint("load_query")
async def load_query(query: str):
    return {"query": query, "normalized": query.lower()}


@checkpoint("search")
async def search(data: dict):
    results = [
        "Waypoint provides agent execution recovery",
        "Event sourcing enables deterministic replay",
    ]
    return {**data, "results": results}


@checkpoint("summarize", cache=True)
async def summarize(data: dict):
    summary = "Waypoint is a fault-tolerant execution recovery system."
    return {**data, "summary": summary}


async def first_run() -> UUID:
    execution_id = await waypoint.create()
    print(f"Created execution: {execution_id}")

    try:
        step1 = await load_query(query="What is Waypoint?")
        print(f"Step 1 (load_query): {step1}")

        step2 = await search(data=step1)
        print(f"Step 2 (search): {step2}")

        step3 = await summarize(data=step2)
        print(f"Step 3 (summarize): {step3}")

        print(f"\nExecution completed! Total steps: {waypoint.get_step_number()}")
        print(f"Final state: {waypoint.get_state()}")

    except Exception as e:
        print(f"Execution failed: {e}")
        raise

    return execution_id


async def crash_recovery_demo(execution_id: UUID) -> None:
    """
    Simulate a crash after 'search' and before 'summarize'.

    On resume:
      - load_query → cache=False, re-executes (same input → same output)
      - search     → cache=False, re-executes (same input → same output)
      - summarize  → cache=True, served from journal (no recompute)
    """
    print("\n--- CRASH RECOVERY ---")
    print(f"Resuming execution {execution_id}...")

    waypoint2 = Waypoint(base_url=API_BASE_URL, workflow_id=WORKFLOW_ID).use()
    resume = await waypoint2.resume(execution_id)
    print(f"Resumed from step {resume.checkpoint_step}")
    print(f"Recovered state keys: {list(waypoint2.get_state().keys())}")

    step1 = await load_query(query="What is Waypoint?")
    print("Step 1 (load_query, fresh — cache=False): re-executed")

    step2 = await search(data=step1)
    print("Step 2 (search, fresh — cache=False): re-executed")

    step3 = await summarize(data=step2)
    print(f"Step 3 (summarize, CACHED — cache=True): {step3['summary']}")

    print(f"\nRecovery complete! Total steps: {waypoint2.get_step_number()}")
    await waypoint2.aclose()


async def main():
    execution_id = await first_run()
    await crash_recovery_demo(execution_id)
    await waypoint.aclose()


if __name__ == "__main__":
    asyncio.run(main())
