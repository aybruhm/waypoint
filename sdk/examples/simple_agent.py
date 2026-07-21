"""
Simple 3-step agent workflow using the Waypoint SDK.

Prerequisites:
    - Waypoint API running at http://localhost:9654

Usage:
    uv run python -m sdk.examples.simple_agent
"""

import asyncio

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


async def main():
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

    await waypoint.aclose()


if __name__ == "__main__":
    asyncio.run(main())
