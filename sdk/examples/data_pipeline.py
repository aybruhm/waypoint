"""
Nightly data sync pipeline — non-AI, ETL workflow.

Prerequisites:
    - Waypoint API running at http://localhost:9654

Usage:
    uv run python -m sdk.examples.data_pipeline

This example demonstrates:
    - Standalone @checkpoint decorator (same pattern as simple_agent)
    - cache=True on IO-bound steps that are expensive to retry (external API fetch,
      CPU-bound normalization)
    - cache=False on idempotent mutation steps (DB upsert, notification)

Crash recovery scenario:
    If the process crashes after normalize_records but before validate_schema:
      - fetch_records    → cache=True, replayed from journal (no re-fetch)
      - normalize_records → cache=True, replayed from journal (no recompute)
      - validate_schema  → cache=False, runs fresh on the recovered records
      - upsert_records   → cache=False, runs fresh (idempotent)
      - send_notification → cache=False, runs fresh
"""

import asyncio
from uuid import UUID

from sdk import Waypoint, checkpoint

WORKFLOW_ID = "data_pipeline"
API_BASE_URL = "http://localhost:9654/api/v1/"

waypoint = Waypoint(
    base_url=API_BASE_URL,
    workflow_id=WORKFLOW_ID,
).use()


@checkpoint("fetch_records", cache=True)
async def fetch_records(source_url: str) -> dict:
    """Fetch records from a slow, rate-limited external API. Cached to avoid re-fetching on crash."""

    print("  Fetching from external API (slow)...")
    await asyncio.sleep(0.1)
    return {
        "source_url": source_url,
        "records": [
            {"id": 1, "name": "  Alice  ", "revenue": 1200.50},
            {"id": 2, "name": "Bob", "revenue": 840.00},
            {"id": 3, "name": "Carol ", "revenue": 2100.75},
        ],
        "fetched_at": "2026-07-22T00:00:00Z",
    }


@checkpoint("normalize_records", cache=True)
async def normalize_records(raw: dict) -> dict:
    """Normalize field names and types. CPU-bound and deterministic — safe to cache."""

    records = [
        {
            "id": r["id"],
            "name": r["name"].strip().lower(),
            "revenue_cents": int(r["revenue"] * 100),
        }
        for r in raw["records"]
    ]
    return {"records": records, "source_url": raw["source_url"]}


@checkpoint("validate_schema", cache=False)
async def validate_schema(normalized: dict) -> dict:
    """Validate that all required fields are present. Fast and stateless — no cache needed."""

    required = {"id", "name", "revenue_cents"}
    invalid = [r for r in normalized["records"] if not required.issubset(r)]
    if invalid:
        raise ValueError(f"Schema validation failed for {len(invalid)} records")
    return {**normalized, "valid": True, "record_count": len(normalized["records"])}


@checkpoint("upsert_records", cache=False)
async def upsert_records(validated: dict) -> dict:
    """Upsert records into the database. Idempotent — safe to re-run, no cache needed."""
    await asyncio.sleep(0.02)
    return {
        "upserted": validated["record_count"],
        "source_url": validated["source_url"],
    }


@checkpoint("send_notification", cache=False)
async def send_notification(summary: dict) -> dict:
    """Send a Slack notification with the sync summary."""
    print(
        f"  Notifying team: {summary['upserted']} records synced from {summary['source_url']}"
    )
    return {"notified": True, "message": f"Synced {summary['upserted']} records"}


async def first_run() -> UUID:
    execution_id = await waypoint.create(
        initial_input={"source_url": "https://api.example.com/customers"}
    )
    print(f"Created execution: {execution_id}")

    raw = await fetch_records(source_url="https://api.example.com/customers")
    print(
        f"Step 1 (fetch_records, cache=True):    {len(raw['records'])} records fetched"
    )

    normalized = await normalize_records(raw=raw)
    print(
        f"Step 2 (normalize_records, cache=True): {len(normalized['records'])} records normalized"
    )

    validated = await validate_schema(normalized=normalized)
    print(
        f"Step 3 (validate_schema, cache=False):  {validated['record_count']} records valid"
    )

    summary = await upsert_records(validated=validated)
    print(
        f"Step 4 (upsert_records, cache=False):   {summary['upserted']} records upserted"
    )

    notification = await send_notification(summary=summary)
    print(f"Step 5 (send_notification, cache=False): {notification['message']}")

    print(f"\nPipeline complete! Total steps: {waypoint.get_step_number()}")
    return execution_id


async def crash_recovery_demo(execution_id: UUID) -> None:
    """
    Resume after a simulated crash between normalize_records and validate_schema.

    fetch_records and normalize_records are served from the journal — no
    external API call, no recompute. The remaining steps run fresh.
    """
    print("\n--- CRASH RECOVERY ---")
    print(f"Resuming execution {execution_id}...")

    waypoint2 = Waypoint(base_url=API_BASE_URL, workflow_id=WORKFLOW_ID).use()
    resume = await waypoint2.resume(execution_id)
    print(f"Resumed from step {resume.checkpoint_step}")
    print(f"Recovered state keys: {list(waypoint2.get_state().keys())}")

    raw = await fetch_records(source_url="https://api.example.com/customers")
    print("Step 1 (fetch_records,    CACHED): no external API call made")

    normalized = await normalize_records(raw=raw)
    print("Step 2 (normalize_records, CACHED): no recompute")

    validated = await validate_schema(normalized=normalized)
    print(
        f"Step 3 (validate_schema,  fresh):  re-validated {validated['record_count']} records"
    )

    summary = await upsert_records(validated=validated)
    print(f"Step 4 (upsert_records,   fresh):  {summary['upserted']} records upserted")

    notification = await send_notification(summary=summary)
    print(f"Step 5 (send_notification, fresh):  {notification['message']}")

    print(f"\nRecovery complete! Total steps: {waypoint2.get_step_number()}")
    await waypoint2.aclose()


async def main():
    execution_id = await first_run()
    await crash_recovery_demo(execution_id)
    await waypoint.aclose()


if __name__ == "__main__":
    asyncio.run(main())
