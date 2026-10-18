"""
Agent workflow with mocked LLM calls, demonstrating crash recovery.

Prerequisites:
    - Waypoint API running at http://localhost:9654

Usage:
    uv run python -m sdk.examples.agent_with_llm_mock

This simulates:
    1. Create a new execution
    2. Normal execution with an LLM call
    3. Resume after a simulated crash: the LLM response is served from cache
"""

import asyncio

from sdk import Waypoint, checkpoint

WORKFLOW_ID = "llm_agent"
API_BASE_URL = "http://localhost:9654/api/v1/"

waypoint = Waypoint(
    base_url=API_BASE_URL,
    workflow_id=WORKFLOW_ID,
).use()


@checkpoint("load_context", cache=True)
async def load_context(user_query: str):
    return {
        "query": user_query,
        "context": {"user_id": "abc123", "session": "test"},
    }


async def mock_llm_call(prompt: str) -> dict:
    """Simulate an expensive LLM API call."""
    await asyncio.sleep(0.05)
    return {
        "response": f"Analysis of: {prompt[:50]}...",
        "tokens_used": 150,
        "model": "gpt-4",
    }


@checkpoint("call_llm", cache=True)
async def call_llm(context: dict):
    print("  Calling LLM (this is expensive)...")
    return await mock_llm_call(context["query"])


@checkpoint("format_output")
async def format_output(data: dict):
    response = data["llm"]["response"]
    return {"formatted": f"<result>{response}</result>", "meta": data["llm"]}


async def first_run():
    """First execution: create, run steps, return execution_id for recovery demo."""
    execution_id = await waypoint.create()
    print(f"Created execution: {execution_id}")

    context = await load_context(user_query="What is event sourcing?")
    print("Step 1 (load_context): context loaded")

    llm_result = await call_llm(context=context)
    print("Step 2 (call_llm): LLM responded")

    output = await format_output(data={"llm": llm_result, "context": context})
    print(f"Step 3 (format_output): {output['formatted'][:100]}...")

    print(f"\nExecution completed! Total steps: {waypoint.get_step_number()}")
    return execution_id


async def crash_recovery_demo(execution_id):
    """
    Simulate a crash and recovery.
    A new Waypoint instance resumes the execution; the cached LLM response
    is returned without re-invoking the LLM call.
    """
    print("\n--- CRASH RECOVERY ---")
    print(f"Resuming execution {execution_id}...")

    waypoint2 = Waypoint(base_url=API_BASE_URL, workflow_id=WORKFLOW_ID).use()

    resume = await waypoint2.resume(execution_id)
    print(f"Resumed from step {resume.checkpoint_step}")
    print(f"Recovered state keys: {list(waypoint2.get_state().keys())}")

    context = await load_context(user_query="What is event sourcing?")
    print("Step 1 (load_context, cached): context loaded (from cache)")

    llm_result = await call_llm(context=context)
    print("Step 2 (call_llm, cached): LLM responded (from cache, no re-execution)")

    output = await format_output(data={"llm": llm_result, "context": context})
    print(f"Step 3 (format_output, fresh): {output['formatted'][:100]}...")

    print(f"\nRecovery complete! Total steps: {waypoint2.get_step_number()}")
    await waypoint2.aclose()


async def main():
    execution_id = await first_run()
    await crash_recovery_demo(execution_id)
    await waypoint.aclose()


if __name__ == "__main__":
    asyncio.run(main())
