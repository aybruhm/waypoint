# RFC: Waypoint — Agent Execution Recovery via Event Sourcing

**Author:** [Abraham Israel](https://github.com/aybruhm/)

**Date:** May 2026

---

## 1. Problem Statement

**Current state:** Agent systems (LLM-driven workflows) executing in production face three critical failure modes:

1. **Non-deterministic cost waste** – Crashes mid-execution result in partial LLM token consumption with no recovery path. Re-running the entire workflow re-invokes already-completed LLM calls, doubling costs.
2. **Opaque state loss** – Naive snapshot-based recovery provides no execution history. Debugging *why* an agent failed requires manual trace reconstruction.
3. **Non-idempotent recovery** – Standard async frameworks (Celery, task queues) lack agent-specific semantics. Retrying a crashed step may re-execute external tool calls with side effects (API mutations, writes).

**Target use case:** A FastAPI-based agent orchestrator that can crash at any point (process kill, OOM, network partition) and resume *deterministically* from the last successful checkpoint without re-executing prior steps or re-calling LLMs.

---

## 2. Goals

- **G1:** Recover from crashes by replaying execution from the last completed checkpoint, without re-invoking deterministic operations (LLM calls, completed tool invocations).
- **G2:** Provide complete execution history (all events, state mutations, decision points) queryable by step/timestamp for debugging.
- **G3:** Support agent-specific semantics: cached LLM responses, tool invocation idempotency, context window management.
- **G4:** Minimal performance overhead: checkpoint writes should not be the critical path bottleneck (< 50ms per step).
- **G5:** Framework-agnostic SDK: usable with any async Python agent framework (LangChain, CrewAI, custom).

---

## 3. Non-Goals

- Distributed workflow orchestration (Temporal scale). Single-process, single-machine focus.
- Real-time monitoring dashboards (phase 2).
- Multi-tenant isolation or RBAC (assume single user/org per instance).
- Handling data inconsistency from partially-executed side effects (assume idempotent tools; explicit acknowledgment of limits).

---

## 4. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Agent Execution Layer                      │
│  (FastAPI async handlers, LangChain/custom agent logic)       │
└──────────────────────────┬───────────────────────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Waypoint SDK       │
                │  (@checkpoint       │
                │   decorators,       │
                │   async context)    │
                └──────────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    ┌───▼────┐      ┌─────▼────┐      ┌─────▼─────┐
    │Event   │      │Checkpoint│      │Replay     │
    │Journal │      │Manager   │      │Engine     │
    │(Append-│      │(LRU,     │      │(Determine-│
    │only)   │      │durability)       │istic exec)│
    └───┬────┘      └─────┬────┘      └─────┬─────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                ┌──────────▼──────────┐
                │  PostgreSQL Store   │
                │  (events, metadata) │
                └─────────────────────┘
```

**Core components:**

1. **Event Journal:** Append-only log. Each step logs: `(step_id, step_name, input, output, side_effects, timestamp, status)`.
2. **Checkpoint Manager:** Tracks "last successful step." On crash, reads checkpoint and resumes from next step.
3. **Replay Engine:** Given a checkpoint, reconstructs agent state deterministically without re-executing prior steps.
4. **SDK:** Decorators + context managers to instrument agent code with minimal changes.

---

## 5. Core Concepts

### 5.1 Event Journal

An immutable, append-only log stored in PostgreSQL. Each agent execution produces a sequence of events:

```
Event 1: Step started (load_context)
Event 2: Step completed (output: {...}, status: success)
Event 3: Step started (call_llm)
Event 4: Step completed (output: "response...", status: success, cached: false)
Event 5: Step started (process_result)
[CRASH OCCURS]
```

On recovery, read events 1–4, skip re-execution, start at step 5.

### 5.2 Checkpoints

A checkpoint is a **pointer to a completed step** with associated state snapshot:

```json
{
  "execution_id": "exec_12345",
  "checkpoint_step": 4,
  "last_completed_at": "2026-05-24T10:15:30Z",
  "state_hash": "sha256(...)",
  "resumable": true
}
```

On crash, load the checkpoint, resume from step 5.

### 5.3 Replay

Replay reconstructs state from events without re-executing:

```python
# Normal execution path (first run)
step_1_output = await step_1(input_data)  # Executes, logs event
step_2_output = await step_2(step_1_output)  # Executes, logs event

# Replay path (after crash from checkpoint 1)
step_1_output = events[0].output  # Read from journal, no execution
step_2_output = await step_2(step_1_output)  # Resume from here
```

---

## 6. Data Model

### 6.1 Database Schema

```sql
-- execution: top-level agent run
CREATE TABLE execution (
  id UUID PRIMARY KEY,
  agent_id VARCHAR NOT NULL,
  status VARCHAR, -- 'running', 'completed', 'failed'
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  initial_input JSONB,
  created_at TIMESTAMP
);

-- event: individual step execution
CREATE TABLE event (
  id BIGSERIAL PRIMARY KEY,
  execution_id UUID NOT NULL REFERENCES execution(id),
  step_number INT NOT NULL,
  step_name VARCHAR NOT NULL,
  input JSONB,
  output JSONB,
  side_effects JSONB, -- { "tool_calls": [...], "mutations": [...] }
  cached BOOLEAN, -- true if output was replayed
  status VARCHAR, -- 'pending', 'started', 'completed', 'failed'
  error JSONB, -- { "type", "message", "traceback" }
  duration_ms INT,
  created_at TIMESTAMP,
  UNIQUE(execution_id, step_number)
);

-- checkpoint: recovery markers
CREATE TABLE checkpoint (
  id UUID PRIMARY KEY,
  execution_id UUID NOT NULL REFERENCES execution(id),
  step_number INT NOT NULL,
  completed_at TIMESTAMP,
  state_hash VARCHAR, -- SHA-256 of state for integrity
  created_at TIMESTAMP
);
```

### 6.2 Event Structure

```python
@dataclass
class Event:
    execution_id: UUID
    step_number: int
    step_name: str
    input: dict
    output: dict
    status: Literal['pending', 'started', 'completed', 'failed']
    side_effects: dict  # { "tool_calls": [...], "mutations": [...] }
    cached: bool = False  # True if replayed from journal
    error: Optional[dict] = None
    duration_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## 7. API Design

### 7.1 SDK Decorators

```python
from waypoint import Waypoint, checkpoint

wp = Waypoint(execution_id="exec_123", db_url="postgres://...")

@checkpoint(name="load_context", wp=wp)
async def load_user_context(user_id: str):
    # Executed and logged
    return {"user": user_id, "profile": {...}}

@checkpoint(name="call_llm", wp=wp, cache=True)  # cache=True: don't re-call
async def call_llm(context: dict, prompt: str):
    # On replay, returns cached output instead of re-calling
    return await llm.generate(prompt, context)

@checkpoint(name="process_result", wp=wp)
async def process_result(llm_output: str):
    return {"processed": llm_output.lower()}

# Orchestration
async def agent_pipeline(user_id: str):
    context = await load_context(user_id)
    llm_result = await call_llm(context, "Summarize user profile")
    final = await process_result(llm_result)
    return final
```

### 7.2 Recovery Endpoints

```python
@app.post("/executions/{execution_id}/resume")
async def resume_execution(execution_id: UUID):
    """Resume from last checkpoint."""
    checkpoint = await wp.get_last_checkpoint(execution_id)
    result = await wp.replay_from_checkpoint(execution_id, checkpoint.step_number)
    return {"status": "resumed", "result": result}

@app.get("/executions/{execution_id}/history")
async def get_execution_history(execution_id: UUID):
    """Fetch complete event log for debugging."""
    events = await wp.get_events(execution_id)
    return {
        "execution_id": execution_id,
        "steps": [
            {
                "step_number": e.step_number,
                "step_name": e.step_name,
                "status": e.status,
                "cached": e.cached,
                "duration_ms": e.duration_ms,
                "error": e.error,
            }
            for e in events
        ]
    }

@app.post("/executions/{execution_id}/replay-from-step")
async def replay_from_step(execution_id: UUID, step_number: int):
    """Replay from a specific step (for testing)."""
    result = await wp.replay_from_step(execution_id, step_number)
    return {"result": result}
```

---

## 8. Example Workflow with Crash/Recovery

```
Execution: exec_abc123
User: user_456

[Time: 10:00:00] Step 1 (load_context)
  Input: { "user_id": "user_456" }
  Output: { "user": "user_456", "profile": {...} }
  Status: completed
  Event logged.

[Time: 10:00:05] Step 2 (call_llm)
  Input: { "context": {...}, "prompt": "..." }
  Output: { "response": "..." }
  Status: completed
  Event logged.
  Checkpoint created: step_number=2

[Time: 10:00:10] Step 3 (process_result)
  Input: { "llm_output": "..." }
  [CRASH: Process killed, connection lost]

---

[Time: 10:00:15] Recovery Initiated
  Read checkpoint: step_number=2
  Load events 1–2 from journal
  Reconstruct state from Event 2 output
  Resume execution at Step 3

Step 3 (process_result) [REPLAY]
  Input: { "llm_output": "..." }  [from Event 2]
  Output: { "processed": "..." }
  Status: completed
  Event logged.

Execution completed successfully.
```

---

## 9. Alternatives Considered

| Alternative | Pros | Cons |
|---|---|---|
| **Snapshot-based recovery** | Simple, no event log overhead | No execution history; wastes on crashes (re-calls LLMs) |
| **Temporal** | Battle-tested, distributed | Overkill for single-machine; complexity; learning curve |
| **Celery + Redis** | Standard Python async | No agent-specific semantics; caching LLM outputs is hacky |
| **Custom watermarking + state save** | Lightweight | Manual, error-prone, no standardization |
| **Event sourcing (full)** | Complete history, audit trail | Storage overhead; complexity for simple agents |

**Decision:** Event sourcing with agent-specific caching semantics balances simplicity and robustness.

---

## 10. Implementation Phases

**Phase 1 (MVP):** Event journal + basic checkpoint + sync replay.
- Single execution at a time.
- PostgreSQL only.
- Minimal error handling.

**Phase 2:** Async replay, concurrent executions, monitoring.

**Phase 3:** Dashboard, advanced filtering, performance optimization.

---

## 11. Success Criteria

- ✅ Agent crashes at step N; resumed from step N+1 without re-calling LLM or duplicating side effects.
- ✅ Execution history queryable; debugging timeline visible.
- ✅ Checkpoint write latency < 50ms per step.
- ✅ Works with LangChain and custom async agents with <5 LOC changes.
- ✅ End-to-end test: 10-step agent, crash on step 7, recover and complete successfully.

---

## 12. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Non-idempotent tool calls (API creates duplicate) | High | Document assumption: all tools must be idempotent or explicit dedup logic required |
| State divergence on partial step execution | High | Checkpoint *after* step completion; never mid-step |
| PostgreSQL becomes bottleneck | Medium | Batch event writes; async I/O; measure latency |
| LLM response cache invalidation (model version change) | Medium | Include model metadata in cache key; versioning strategy |

---

## References

- Designing Data-Intensive Applications (Kleppmann) — Event sourcing, Transactional Outbox Pattern
    - https://www.oreilly.com/library/view/designing-data-intensive-applications/9781098119058/
    - https://microservices.io/patterns/data/transactional-outbox.html
    - https://www.conduktor.io/glossary/outbox-pattern-for-reliable-event-publishing
    - https://medium.com/@ichsan.said/using-event-sourcing-transactional-outbox-pattern-in-event-driven-architecture-pros-cons-56dada9a4301
- [Temporal Workflow Documentation — Durable execution patterns](https://docs.temporal.io/workflows)
