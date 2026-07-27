# Waypoint

A Python SDK for building fault-tolerant multi-step workflows via event sourcing.

When a workflow crashes mid-execution, Waypoint resumes from the last successful step, without re-running expensive operations that already completed. Every step's input and output is logged to an append-only PostgreSQL journal; on recovery, the journal is replayed from the last checkpoint.

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
# 3-step search workflow with crash recovery
uv run python -m sdk.examples.simple_agent

# Mocked LLM + crash recovery demo
uv run python -m sdk.examples.agent_with_llm_mock

# Nightly ETL sync: cache=True on expensive external API fetch
uv run python -m sdk.examples.data_pipeline

# E-commerce order pipeline: WaypointSession + cache on payment to prevent double-charge
uv run python -m sdk.examples.order_processing

# RAG pipeline: @waypoint.checkpoint instance decorator + class-based steps
uv run python -m sdk.examples.document_rag
```

See [`sdk/examples/`](sdk/examples/) for the full source of each example, including crash recovery demos.

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

Any multi-step process where re-running from scratch is expensive, slow, or dangerous:

1. **Wasted computation**: Steps that succeeded before the crash get re-run on retry: re-fetching from slow APIs, re-processing records, re-calling LLM endpoints.
2. **Lost state**: No record of which step failed, what the inputs were, or how far execution got.
3. **Duplicate side effects**: Retrying a workflow that already charged a card, sent an email, or wrote to an external system creates duplicates or breaks idempotency.

Waypoint avoids all three by persisting every step's result. On crash, resume from the checkpoint: completed steps return their stored outputs instantly and execution continues from the next uncompleted step.

---

## Architecture

```
Workflow Code
    ↓
@checkpoint decorators (Waypoint SDK)
    ↓
+----------------+-----------------+------------------+
| Event Journal  | Checkpoint Mgr  | Replay Engine    |
| (append-only)  | (progress)      | (deterministic)  |
+----------------+-----------------+------------------+
    ↓
PostgreSQL
```

For the full breakdown: component reference, data model, and runtime communication flows, see [docs/architecture.md](docs/architecture.md).

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Execution** | A single run of a workflow, identified by a UUID. |
| **Step** | A decorated async function (`@checkpoint("name")`). Each step runs at most once per execution. |
| **Checkpoint** | A persisted record of a step's input/output + execution position. |
| **Event Journal** | Append-only log of all steps across all executions (PostgreSQL). |
| **Replay** | Reconstructing state by reading checkpoints in order, without re-executing steps. |

---

## How It Works

```python
@checkpoint("step_name", cache=True)
async def my_step(input: dict) -> dict:
    return output
```

The decorator:
1. Checks if a checkpoint exists for this step in the current execution.
2. If yes and `cache=True`: returns stored output immediately (no re-execution).
3. If no: runs the function, persists input/output as a checkpoint, returns output.

On crash, create a new `Waypoint` instance and call `resume(execution_id)`. The SDK rebuilds state from the journal and continues from the next uncompleted step.

---

## Integration Patterns

**Standalone decorator**: simplest, steps registered at module level:

```python
waypoint = Waypoint(base_url=..., workflow_id="my_pipeline").use()

@checkpoint("fetch_data", cache=True)
async def fetch_data(url: str) -> dict: ...
```

**Instance decorator**: steps explicitly bound to a specific `Waypoint` instance:

```python
waypoint = Waypoint(base_url=..., workflow_id="my_pipeline")

@waypoint.checkpoint("fetch_data", cache=True)
async def fetch_data(url: str) -> dict: ...
```

**Session context manager**: scopes a series of steps to a single execution, useful when steps are defined as plain functions rather than decorated at import time:

```python
async with waypoint.session(execution_id) as sess:
    result = await sess.async_execute("step_name", {"arg": val, "__callable__": fn}, cache=True)
```

---

## Key Properties

- **Deterministic replay**: Same inputs always produce the same outputs; completed steps never re-execute.
- **Step output caching**: Outputs marked `cache=True` are served from the journal on replay (zero re-computation cost).
- **Non-idempotent step protection**: Mark payment charges, email sends, or any one-shot side effect as `cache=True` to guarantee they run at most once across retries.
- **Framework-agnostic**: Works with LangChain, CrewAI, FastAPI, plain asyncio, or any async Python code.
- **Minimal integration**: Add `@checkpoint` to each step. ~3 lines of change per step.
- **Full history**: Query every step, error, duration, and state transition by execution ID.

---

## When to Use

- Long-running workflows (minutes to hours) where restarting from scratch is expensive.
- Cost-sensitive pipelines where re-running steps wastes money (LLM API calls, paid data sources, cloud processing).
- Financial or transactional workflows where duplicate side effects (double charges, duplicate sends) must be prevented.
- ETL jobs where the extraction phase is slow or rate-limited and re-fetching on failure is unacceptable.
- Teams needing a full audit trail of step inputs, outputs, and errors for debugging.

---

## When Not to Use

- Distributed/multi-machine workflows (Waypoint is single-process per execution).
- Stateless, fire-and-forget tasks with no recovery requirement: if a task fails you're happy restarting it from scratch, use Celery, SQS, or similar.
- Simple linear scripts with no expensive steps and no side effects worth protecting.

