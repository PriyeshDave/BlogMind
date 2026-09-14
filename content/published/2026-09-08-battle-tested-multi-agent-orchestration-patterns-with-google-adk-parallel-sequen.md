---
contrarian: false
generated_at: '2026-09-08T13:23:26.276240+00:00'
pillar: architecture
sources:
- https://github.com/Nandinibajaj28/adk-multiagent-architecture
- https://github.com/reference-architecture-ai/reference-architecture.ai
status: published
subtitle: A walkthrough of real code and patterns for orchestrating advanced multi-agent
  systems with Google ADK, solving problems that break most single-agent setups.
title: 'Battle-Tested Multi-Agent Orchestration Patterns with Google ADK: Parallel,
  Sequential, and Persistent Sessions'
---

```markdown
# Multi-Agent Orchestration with Google ADK: Patterns That Don’t Break at Scale

_Solving orchestration gaps that block productionizing ADK agents, with runnable code, real numbers, and field-tested lessons._

## Google ADK's Agent Primitives Aren’t Enough for Real Orchestration

Google’s Agent Development Kit (ADK) ships good agent-building primitives: agent factories, tool APIs, agent-to-agent calls, and basic integrations. What it doesn’t provide are orchestration strategies that hold up in production. Its default patterns focus on call chains or basic "task bots," assuming minimal state, simple call order, and zero robustness.

Try real workflows—parallel subtasks, persistent multi-session state, dynamic agent switching—and the base abstractions collapse. Production orchestration requires agent isolation, coordinated state, robust result handling, and routing that doesn’t devolve into Python spaghetti. ADK provides the hammers; orchestration is your problem.

## Parallel Agent Execution Demands Explicit Control—Naive Threads Fail

[`nandinibajaj28/adk-multiagent-architecture`](https://github.com/Nandinibajaj28/adk-multiagent-architecture) shows why parallel execution isn’t just threading or async. Coordination, race conditions, DB locks, and aggregation all force hands-on management.

A stripped-down but working pattern from the codebase:

```python
import threading
import queue

from agents.agent_factory import AgentFactory
from persistence.sqlite_handler import SQLiteHandler

def worker(agent_id, task, result_queue, db_path):
    agent = AgentFactory.create(agent_id)
    sqlite_handler = SQLiteHandler(db_path)
    with sqlite_handler.transaction():
        result = agent.run(task)
        sqlite_handler.save_result(agent_id, result)
        result_queue.put((agent_id, result))

def execute_parallel(tasks, agents, db_path):
    result_queue = queue.Queue()
    threads = []
    for agent_id, task in zip(agents, tasks):
        t = threading.Thread(target=worker, args=(agent_id, task, result_queue, db_path))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    results = {}
    while not result_queue.empty():
        agent_id, result = result_queue.get()
        results[agent_id] = result
    return results
```

Without explicit transaction boundaries and queue-based collection, concurrent writes to SQLite will fail with `sqlite3.OperationalError: database is locked`. The repo's approach forces local serialization on DB I/O to sidestep SQLite’s broken concurrency. ADK doesn’t handle this: you need coordination or you’ll see lock errors and data loss.

## Inline Routing Chains Collide With Real-World Logic Changes

Chaining agents inline—a common beginner move, e.g., `result = agent2(agent1(input))`—collapses when the routing requires dynamic selection, error retries, or any post-processing. This fragile spaghetti can’t absorb workflow changes.

The repository’s router decouples the workflow from the agents. The core pattern:

```python
class WorkflowRouter:
    def __init__(self, agent_sequence):
        self.agent_sequence = agent_sequence

    def run(self, input_data, session_id):
        data = input_data
        for agent_id in self.agent_sequence:
            agent = AgentFactory.create(agent_id)
            data = agent.run(data, session_id=session_id)
        return data
```

Routing is declarative: provide a list of agent IDs, inject context, and the router steps the data through the pipeline. This structure supports agent graphs, traceability, and avoids inline dependencies.

## SQLite Persistence Works—Until You Push Concurrency

Most multi-agent orchestrators avoid persistent state or punt to in-memory session maps, which break under multi-request sessions or restarts. This codebase uses plain SQLite, skipping Redis/PSQL overhead for agent state that rarely justifies it.

Core implementation:

```python
import sqlite3
from contextlib import contextmanager

class SQLiteHandler:
    def __init__(self, db_path):
        self.db_path = db_path

    @contextmanager
    def transaction(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        c = conn.cursor()
        try:
            yield c
            conn.commit()
        finally:
            conn.close()

    def save_result(self, agent_id, result, session_id=None):
        with self.transaction() as c:
            c.execute(
                'INSERT INTO results (agent_id, result, session_id) VALUES (?, ?, ?)',
                (agent_id, result, session_id)
            )
```

SQLite handles basic isolation for single-node, low-throughput jobs. But its [locking model](https://sqlite.org/howtocorrupt.html) breaks for multi-writer concurrency; you’ll hit `database is locked` unless all writes are serialized. WAL mode buys some time, but distributed or high-scale concurrency will break this pattern.

## Architecture: Concrete Roles for Each Component

The core pieces:

- **ADK Agent Primitives:** Define agent skills and tools, but do not own orchestration or state.
- **Workflow Router:** Holds workflow definitions (agent ID sequences, logic policies) and invokes agents in proper order, passing shared context and results.
- **Persistence Layer:** Writes inputs, outputs, workflow metadata, and session state to SQLite using transactional APIs.
- **Session Management:** Every request issues or accepts a session ID for all DB ops and cross-agent calls, ensuring traceability and recovery.
- **Parallel/Sequential Controller:** Orchestrator chooses—per workflow—parallel agent execution (with `execute_parallel`) or sequential traversal (via the router).
- **API Layer:** Thin HTTP layer exposes orchestration. Receives input, resolves agents and workflows, persists and returns results.

Operational flow: API request → router picks or builds agent sequence → orchestrator runs agents in parallel or sequence → everything tracked in SQLite per session → results, sessions, and artifacts returned and logged.

## Where Single-Agent Patterns Shatter

Major pain points arise fast:

- **Concurrency Control:** Naive parallelism explodes without transactional locking, especially with file-based DBs like SQLite.
- **Flexible Routing:** Hardcoding agent handoffs can’t handle even modest workflow complexity. Declarative routing or agent graphs are required.
- **Persisted State:** In-memory tricks fail as soon as session continuity or recovery is needed. Even a simple persistent DB takes you far.
- **Session Isolation:** No session context? No recovery, no traceability, no multi-step workflows.
- **Observability:** Multi-agent flows demand structured logs and per-step state tracking—or debugging becomes impossible.
- **Infra Coupling:** Orchestrators hard-locked to sequence-only chains or HTTP-only triggers slow evolution as agents multiply.

Single-agent chains don’t scale or survive real usage. Invest in real orchestration early: explicit invocation, parallelization, persistent state, and robust session management save you from painful rework.

Google ADK is a strong base, but production multi-agent workflows require deliberate orchestration architecture. Patch these gaps or expect brittle systems and firefighting down the road.
```