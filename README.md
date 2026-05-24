# [PoC] Waypoint: Agent Execution Recovery via Event Sourcing

**Waypoint** is a lightweight Python SDK for building fault-tolerant LLM agent workflows. It enables agent systems to recover from crashes by replaying execution from checkpoints, without re-invoking deterministic operations like LLM calls or completed tool invocations.

### Problem It Solves

When an LLM-driven agent workflow crashes mid-execution:

1. **Cost waste** – Prior LLM calls have consumed tokens but produced no usable output. Naive retry logic re-calls the LLM, wasting money.
2. **Opaque state loss** – No execution history means manual debugging. What step failed? What was the intermediate state?
3. **Duplicate side effects** – Retrying a tool invocation (e.g., API write) may create duplicates or violate idempotency constraints.

Waypoint solves this with an immutable event journal that logs every step's input/output. On crash, the system reads the checkpoint, reconstructs the agent state from cached outputs, and resumes deterministically from the next step—no re-execution, no duplicate costs.

### Key Features

- **Event-sourced execution** – Every step is logged to an append-only journal in PostgreSQL.
- **Deterministic replay** – State is reconstructed from cached events without re-executing prior steps.
- **LLM response caching** – LLM outputs are cached; replay returns cached responses instantly (zero re-call cost).
- **Minimal SDK footprint** – Drop-in decorator (`@checkpoint`) requires <5 LOC changes to agent code.
- **Framework-agnostic** – Works with LangChain, CrewAI, custom async agents, FastAPI, etc.
- **Complete execution history** – Query the full timeline of steps, errors, and state transitions for debugging.
- **Checkpoint-based recovery** – Resume from the last successful step with one API call.

### Use Cases

1. **Long-running agent workflows** – Agents that orchestrate multiple LLM calls and tool invocations over minutes/hours. Crashes are costly; recovery is essential.
2. **Cost-sensitive applications** – Minimize wasted LLM tokens on retries. Cache responses, replay instantly.
3. **Observability & debugging** – Full execution history helps teams understand agent behavior, failure modes, and bottlenecks.
4. **Agent-as-a-service** – SaaS platforms running user-submitted agents need reliable, auditable execution.

### Positioning vs Alternatives

| Tool | Scope | Best For | Trade-off |
|------|-------|----------|-----------|
| **Waypoint** | Single-machine, event-sourced recovery | Agent workflows, cost optimization | Single-process, limited scale |
| **Temporal** | Distributed, general workflow orchestration | Microservices, complex routing | Overkill for agents, learning curve |
| **Celery + Redis** | Distributed task queue | Background jobs, work distribution | No agent semantics, manual caching |
| **LangChain Memory** | In-memory state mgmt | Conversation history | Volatile, no crash recovery |

**Waypoint's differentiator:** Agent-first design. Checkpoints are cheap, replay is deterministic, LLM calls are cached, and the API is dead simple.

### Technical Stack

- **Language:** Python 3.10+
- **Async runtime:** asyncio
- **Framework:** FastAPI (for demo), but framework-agnostic
- **Database:** PostgreSQL (append-only event log, checkpoint tracking)
- **Serialization:** Pydantic, JSON

### Architecture

```
Agent Code
    ↓
@checkpoint decorators (Waypoint SDK)
    ↓
┌─────────────────┬──────────────────┬────────────────┐
│ Event Journal   │ Checkpoint Mgr   │ Replay Engine  │
│ (append-only)   │ (track progress) │ (deterministic)│
└─────────────────┴──────────────────┴────────────────┘
    ↓
PostgreSQL (events, checkpoints, metadata)
```

### Success Metrics

- Agent crashes on step 5 of 10; resumes from step 5 without re-executing steps 1–4.
- Checkpoint write latency < 50ms.
- Full execution history queryable for any execution ID.
- Zero code changes to agent logic (besides adding `@checkpoint` decorators).

### Target Audience

- **Backend engineers** building LLM agent APIs with FastAPI.
- **ML platform teams** running user-submitted agents or multi-step workflows.
- **AI startups** optimizing LLM token usage and reliability.

### License

[BSD 2-Clause](./LICENSE)

