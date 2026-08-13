---
contrarian: false
generated_at: '2026-08-13T21:21:09.417321+00:00'
pillar: architecture
sources:
- https://news.ycombinator.com/item?id=45329322
- https://github.com/rowboatlabs/rowboat
- https://github.com/airweave-ai/airweave
status: pending_review
subtitle: Practical, code-first guide to architecting agent memory with SQL, from
  schema to query, showing why and how it's a real alternative to vector and graph
  stores.
title: Why We Ditched Vectors and Graphs for SQL in Agent Memory Systems
---

# Why We Ditched Vectors and Graphs for SQL in Agent Memory Systems

**Practical, code-first guide to architecting agent memory with SQL, from schema to query, showing why and how it’s a real alternative to vector and graph stores.**

## Vector and Graph Memories Fail for Structured Agent State

Vector and graph-based agent memories get too much credit for handling agent memory. Embeddings work for dense semantic search, but agents rarely need "fetch a vaguely similar past task." They need precise context: *when did this subgoal run? what did the tool call return? what failures followed?* Vector recall flattens distinct episodes, loses any notion of order, and can't reliably fetch concrete data. 

Graph memories—LangGraph and similar models—promise structure, but agent traces are almost always linear. Traces as graphs usually collapse to a table; real branching is rare. Custom graphs fall apart at scale or require DSLs that bloat complexity. In production, dumping >50,000 tool calls in a property graph is slow and tedious.

**What breaks:** debugging looping agents as they "learn": vector stores pull similar failures, graph tools only retrace a near-linear path, and root cause hides among a fixed set of steps—when all you want is `WHERE tool_call='search' AND result CONTAINS 'timeout' AND timestamp > x`.

## SQL Is Superior for Episodic, Traceable Agent Memory

SQL wins for episodic, relational, and auditable agent logs. In trace-heavy agent workloads, you need:
- Traceability: Link every action and observation by run/session.
- Arbitrary Query: Filter by any field, not just semantic nearness.
- Temporal/Relational Analysis: Range querying, joins on tool, user, or error.
- Reproducibility and Audit: Store raw data, replay full traces, audit every move.

Audit can't be optional. Tool-using agents demand high-integrity logs and explicit transitions. Graph stores make schema changes painful. Vectors drop key data on embedding; only the raw string survives. SQL stores all context, is schema-flexible, and can index everything you need.

**Real-world win:** To replay a user for debugging/compliance, SQL needs five lines to pull every step for `user_id=123, run between 12-2pm, failed >2 times`. Vector stores offer only "similar" steps. Graph traversal crumbles with large volumes.

## SQL Memory Layer Is the Backbone: Agent Loop Architecture

Agent action/observation cycles look like this:

```
Agent   ↔ [Memory Layer] ↔ [Environment/Tools]
```

### Typical Vector Store Setup

1. Agent encodes state as embedding.
2. Stores embedding + metadata in vector DB.
3. Queries yank "close" states later.

```
[Agent]
   |
  (to embedding)
   |
[Vector Store]
   |
(recall similar states, metadata filtering optional)
   |
[Action]
```

**Blocker:** You can’t fetch "run where I called tool X and got error Y after event Z."

### SQL Table Setup

1. Agent writes each step as a structured row (action, observation, timestamp).
2. Query any field: run_id, tool, parameters, result, user.

```
+-----------------------------------+
|           Agent Loop              |
+-----------------------------------+
        |             ^
   writes step      reads context
        v             |
+------------------------------+
|        SQL Memory Layer      |
|  [actions table:            |
|   id, run_id, timestamp,    |
|   action, params, result]   |
+------------------------------+
        |             ^
    Environment/Tools
```
SQL provides actionable traces. Agents read context (for planning) and write new events. Any field is sliced and filtered. No graph traversal or embedding fiddling required.

## Full Example: Indexing and Querying Agent Memory in SQL

Here’s runnable code for minimal agent memory. SQLite for demo—swap in Postgres for scale.

### SQL Schema

```sql
CREATE TABLE agent_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  action_type TEXT NOT NULL,   -- 'tool_call', 'observation', etc.
  tool_name TEXT,
  tool_params JSON,
  result JSON,
  error TEXT
);
CREATE INDEX idx_run_time ON agent_actions (run_id, timestamp);
CREATE INDEX idx_user ON agent_actions (user_id);
```

### Python: Store and Query Traces

```python
import sqlite3
import json
from datetime import datetime

db = sqlite3.connect(":memory:")  # Use 'filename.db' to persist

def setup_schema(conn):
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action_type TEXT NOT NULL,
                tool_name TEXT,
                tool_params TEXT,   -- JSON stringified
                result TEXT,        -- JSON stringified
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_run_time ON agent_actions (run_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_user ON agent_actions (user_id);
        """)

def record_action(conn, run_id, user_id, action_type, tool_name=None, tool_params=None, result=None, error=None):
    with conn:
        conn.execute(
            """INSERT INTO agent_actions 
            (run_id, user_id, action_type, tool_name, tool_params, result, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, user_id, action_type, tool_name,
                json.dumps(tool_params) if tool_params else None,
                json.dumps(result) if result else None,
                error
            )
        )

def get_actions_for_run(conn, run_id):
    cur = conn.execute(
        "SELECT * FROM agent_actions WHERE run_id = ? ORDER BY timestamp ASC", (run_id,)
    )
    return cur.fetchall()

def query_failures_by_tool(conn, tool_name, since_time):
    cur = conn.execute(
        """
        SELECT * FROM agent_actions
        WHERE tool_name = ?
        AND error IS NOT NULL
        AND timestamp > ?
        """, (tool_name, since_time)
    )
    return cur.fetchall()

if __name__ == "__main__":
    setup_schema(db)
    record_action(
        db, "run1", "user_abc", "tool_call", "search", {"q": "widgets"}, {"hits": 10}, None
    )
    record_action(
        db, "run1", "user_abc", "tool_call", "search", {"q": "widgets"}, None, "timeout"
    )
    record_action(
        db, "run1", "user_abc", "observation", None, None, {"message": "recovered"}, None
    )
    actions = get_actions_for_run(db, "run1")
    print("All actions in run1:")
    for a in actions:
        print(a)
    t_ago = datetime.utcnow().isoformat()
    failures = query_failures_by_tool(db, "search", t_ago)
    print("Recent search tool failures:", failures)
```

This is full-fidelity: filterable history, easier to debug, and trivial to audit. Each run’s actions are instantly retrievable and joinable. No chasing fuzzy scores or complex traversals.

## Known Failure Modes: Scale, Concurrency, Non-Textual Data

SQL is not silver-bullet memory.

**Scaling:**  
SQLite’s ceiling is ~100k writes/sec. Postgres degrades past 10M rows unless partitioned/sharded. For 10M+ episodes/month, use streaming ingest, prune old runs, or go OLAP/partitioned (BigQuery, Redshift).

**Concurrency:**  
High-parallel agent tool usage hits SQLite write locks. Postgres holds up but needs `SERIALIZABLE` for replay, which impacts throughput. Workarounds: async bulk insert, append-only logs, resolve conflicts at read time.

**Non-Text/Semantic Memory:**  
If you need true vector recall—"find things conceptually close"—SQL alone isn’t enough. You can: 1) add an embedding column, or 2) run an external vector DB for semantic search, keeping SQL for structured trace.

Never store files or blobs inline. Store references, not the binary data.

---

SQL isn’t magic. It’s just the right tool for structured, auditable agent memory. For nearly all production agent tool call logs, SQL means less friction, more reliable debugging, and a truly queryable record. Use vectors or graphs only if you actually need dense similarity or massive graph analysis. For the rest, rows win.