# Waypoint

A Python SDK for making LLM agent workflows fault-tolerant via event sourcing.

When an agent crashes mid-execution, Waypoint lets you resume from the last successful step—without re-running LLM calls or tool invocations that already completed. It does this by logging every step's input/output to an append-only PostgreSQL journal, then replaying from checkpoints on recovery.

## Getting Started

### Prerequisites

- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.13+)

### Clone & Start

```sh
git clone git@github.com:aybruhm/waypoint.git
cd waypoint
make up
```

This starts the API gateway on `http://localhost:9654` and PostgreSQL. The gateway auto-reloads on code changes.

### Run Migrations

```sh
make run_migrations
```

### Run Examples

```sh
# 3-step agent, no LLM
uv run python -m sdk.examples.simple_agent

# Mocked LLM + crash recovery demo
uv run python -m sdk.examples.agent_with_llm_mock
```

### Stop

```sh
make down
```

### Makefile Reference

| Command | Description |
|---------|-------------|
| `make up` / `make start` | Build & start containers (detached) |
| `make down` / `make stop` | Stop & remove containers |
| `make run_migrations` | Apply pending Alembic migrations |
| `make revert_migrations` | Roll back last migration |
| `make add_migration MSG="msg"` | Auto-generate new migration |
| `make show_current_db_head` | Show current migration version |
| `make show_db_heads` | List all migration heads |

---

## What It Solves

LLM agent crashes create three problems:

1. **Wasted spend**: LLM calls that succeeded before the crash get re-invoked on retry.
2. **Lost context**: No record of what happened, what state the agent was in, or which step failed.
3. **Duplicate effects**: Retrying a tool call (e.g., an API write) can create duplicates or break idempotency.

Waypoint avoids all three by persisting every step's result. On crash, you resume from the checkpoint—cached LLM responses return instantly, tool outputs are reused, and execution continues from the next step.

---

## Architecture

```
Agent Code
    ↓
@checkpoint decorators (Waypoint SDK)
    ↓
┌────────────────┬─────────────────┬──────────────────┐
│ Event Journal  │ Checkpoint Mgr  │ Replay Engine    │
│ (append-only)  │ (progress)      │ (deterministic)  │
└────────────────┴─────────────────┴──────────────────┘
    ↓
PostgreSQL
```

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Execution** | A single run of an agent workflow, identified by a UUID. |
| **Step** | A decorated async function (`@checkpoint("name")`). Each step runs once per execution. |
| **Checkpoint** | A persisted record of a step's input/output + execution position. |
| **Event Journal** | Append-only log of all steps across all executions (PostgreSQL). |
| **Replay** | Reconstructing state by reading checkpoints in order, skipping re-execution. |

---

## How It Works

```
@checkpoint("step_name")
async def my_step(input):
    return output
```

The decorator:
1. Checks if a checkpoint exists for this step in the current execution.
2. If yes: returns cached output immediately (no function execution).
3. If no: runs the function, persists input/output as a checkpoint, returns output.

On crash, create a new `Waypoint` instance and call `resume(execution_id)`. The SDK rebuilds state from the journal and continues from the next uncompleted step.

---

## Key Properties

- **Deterministic replay** — Same inputs always produce same outputs; no re-execution.
- **LLM call caching** — Cached responses are returned on replay (zero token cost).
- **Framework-agnostic** — Works with LangChain, CrewAI, custom async agents, FastAPI, etc.
- **Minimal integration** — Add `@checkpoint` decorators (one per step). ~3 lines of change per step.
- **Full history** — Query every step, error, and state transition by execution ID.

---

## When to Use

- Long-running agent workflows (minutes to hours) where crashes are expensive.
- Cost-sensitive apps where re-calling LLMs on retry is unacceptable.
- Teams needing audit trails for agent behavior and debugging.
- Agent-as-a-service platforms running untrusted/user-submitted agents.

---

## When Not to Use (Next Steps)

- Distributed/multi-machine workflows (Waypoint is single-process).
- High-throughput task queues (use Celery, Temporal, etc.).
- Simple chatbots with no multi-step orchestration.

---

## Stack

- Python 3.13+
- asyncio
- FastAPI (gateway demo only; SDK is framework-agnostic)
- PostgreSQL (events + checkpoints)
- Pydantic + JSON serialization
