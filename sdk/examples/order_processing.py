"""
E-commerce order processing pipeline — non-AI, financial workflow.

Prerequisites:
    - Waypoint API running at http://localhost:9654

Usage:
    uv run python -m sdk.examples.order_processing

This example demonstrates:
    - WaypointSession context manager: async with waypoint.session(id) as sess
    - sess.async_execute(step_name, {**params, "__callable__": fn}, cache=...)
    - cache=True on a non-idempotent side effect (charge_payment) to prevent
      double-charging a customer on crash recovery
    - sess.results and sess.step_count for post-session introspection

Crash recovery scenario:
    If the process crashes after charge_payment but before reserve_inventory,
    a naive retry would charge the customer twice. cache=True on charge_payment
    means the stored transaction ID is returned on resume — no second API call.
"""

import asyncio
from uuid import UUID

from sdk import Waypoint

WORKFLOW_ID = "order_processing"
API_BASE_URL = "http://localhost:9654/api/v1/"


# ── step implementations (plain async functions, no decoration) ──────────────


async def validate_order(order: dict) -> dict:
    if not order.get("items"):
        raise ValueError("Order must contain at least one item")
    total = sum(item["price"] * item["qty"] for item in order["items"])
    return {**order, "total_cents": int(total * 100), "validated": True}


async def charge_payment(order: dict) -> dict:
    """Non-idempotent — charges the customer's card. Must never run twice."""
    print("  Charging payment card...")
    await asyncio.sleep(0.05)
    return {
        "transaction_id": f"txn_{order['order_id']}_abc123",
        "amount_cents": order["total_cents"],
        "status": "captured",
    }


async def reserve_inventory(order: dict, transaction: dict) -> dict:
    await asyncio.sleep(0.02)
    reserved = [{"sku": item["sku"], "qty": item["qty"]} for item in order["items"]]
    return {
        "reserved": reserved,
        "warehouse": "WH-01",
        "transaction_id": transaction["transaction_id"],
    }


async def dispatch_fulfillment(reservation: dict) -> dict:
    await asyncio.sleep(0.02)
    return {
        "fulfillment_id": f"ful_{reservation['transaction_id']}",
        "items": reservation["reserved"],
        "status": "dispatched",
    }


async def send_confirmation(order: dict, transaction: dict) -> dict:
    print(f"  Sending confirmation to {order['customer_email']}...")
    return {
        "email_sent": True,
        "to": order["customer_email"],
        "transaction_id": transaction["transaction_id"],
    }


# ── pipeline runner ──────────────────────────────────────────────────────────


async def run_order(waypoint: Waypoint, order: dict, execution_id: UUID) -> None:
    """
    Execute the full order pipeline inside a WaypointSession.

    On first run the session detects that the gateway is already initialized (create() was just called) and skips the resume API call. On recovery, the gateway is fresh so the session calls resume() to restore prior state.

    Steps with cache=True check that restored state before executing.
    """
    async with waypoint.session(execution_id) as sess:
        validated = await sess.async_execute(
            "validate_order",
            {"order": order, "__callable__": validate_order},
        )
        print(f"  Step 1 (validate_order):    total = {validated.output['total_cents']} cents")

        charged = await sess.async_execute(
            "charge_payment",
            {"order": validated.output, "__callable__": charge_payment},
            cache=True,  # never charge twice — on resume this returns the stored txn ID
        )
        status = "CACHED" if charged.cached else "fresh"
        print(f"  Step 2 (charge_payment, {status}): txn = {charged.output['transaction_id']}")

        reserved = await sess.async_execute(
            "reserve_inventory",
            {
                "order": validated.output,
                "transaction": charged.output,
                "__callable__": reserve_inventory,
            },
        )
        print(f"  Step 3 (reserve_inventory): warehouse = {reserved.output['warehouse']}")

        dispatched = await sess.async_execute(
            "dispatch_fulfillment",
            {"reservation": reserved.output, "__callable__": dispatch_fulfillment},
        )
        print(f"  Step 4 (dispatch_fulfillment): id = {dispatched.output['fulfillment_id']}")

        confirmation = await sess.async_execute(
            "send_confirmation",
            {
                "order": order,
                "transaction": charged.output,
                "__callable__": send_confirmation,
            },
        )
        print(f"  Step 5 (send_confirmation): sent to {confirmation.output['to']}")

        print(f"\n  Session complete — {sess.step_count} steps recorded.")


async def main():
    order = {
        "order_id": "ORD-9001",
        "customer_email": "customer@example.com",
        "items": [
            {"sku": "WIDGET-A", "qty": 2, "price": 29.99},
            {"sku": "WIDGET-B", "qty": 1, "price": 49.99},
        ],
    }

    waypoint = Waypoint(base_url=API_BASE_URL, workflow_id=WORKFLOW_ID)
    execution_id = await waypoint.create(initial_input={"order_id": order["order_id"]})
    print(f"Created execution: {execution_id}\n")

    print("--- FIRST RUN ---")
    await run_order(waypoint, order, execution_id)

    print("\n--- CRASH RECOVERY ---")
    print("Resuming — charge_payment (cache=True) will NOT be re-attempted.\n")

    waypoint2 = Waypoint(base_url=API_BASE_URL, workflow_id=WORKFLOW_ID)
    await run_order(waypoint2, order, execution_id)

    await waypoint2.aclose()
    await waypoint.aclose()


if __name__ == "__main__":
    asyncio.run(main())
