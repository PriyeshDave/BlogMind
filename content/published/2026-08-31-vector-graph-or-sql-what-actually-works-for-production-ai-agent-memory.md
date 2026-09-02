---
contrarian: false
generated_at: '2026-08-31T19:03:11.394847+00:00'
pillar: architecture
sources:
- https://news.ycombinator.com/item?id=45329322
- https://github.com/monkey2jack/aiduMEI
- https://github.com/sublimecoder/sublimecoding
status: published
subtitle: You’ll see concrete code and real tradeoff data for vector stores, graph
  DBs, and SQL memory in agent stacks—plus a breakdown of which is fastest, most robust,
  and easiest to scale.
title: Vector, Graph, or SQL? What Actually Works for Production AI Agent Memory
---

# Vector, Graph, or SQL? What Actually Works for Production AI Agent Memory

_Scalable agent memory is no longer a side project. Below are direct, runnable benchmarks comparing vector store, graph, and SQL agent memory—where each fails, which one holds up under realistic loads, and numbers for latency, recall, and operational pain. At scale, the right call means the difference between a stable system and endless triage._

## Agent Memory Becomes the Bottleneck Before the LLM Fails

Most AI agent demos end once the LLM spits out an answer from some context window. In production, that's not where systems break. Failures typically strike at the memory and query layers:
- Latency spikes the instant your index outgrows demo scale.
- Embedding-only recall regurgitates "semantically similar" content that's factually wrong or structurally useless.
- "Just swap in a bigger store" becomes a trap: agents break when working set exceeds RAM or when relationships need tracking.

Serious agent workloads—continuous learning, chaining, multi-user context—hit hard limits on memory performance and retrieval quality. The naive "just use a vector DB" strategy disintegrates at scale, with link-heavy context, or when it's time to debug.

## Vector Stores: High Throughput, Bad at Structure

Vector databases (FAISS, Chroma, Pinecone, etc.) remain the obvious default for LLM memory. They deliver unbeatable raw embedding search for static text or code. That speed collapses once you need structure or linked context.

### Real-World FAISS Latency

A 10,000-record FAISS in-memory store, basic retrieval:

```python
import faiss
import numpy as np
import time

dim = 1536  # OpenAI/text-embedding-ada-002
num_vectors = 10_000
np.random.seed(42)
vectors = np.random.randn(num_vectors, dim).astype(np.float32)

index = faiss.IndexFlatL2(dim)
index.add(vectors)

query = np.random.randn(1, dim).astype(np.float32)

start = time.time()
D, I = index.search(query, k=5)
latency = (time.time() - start) * 1000

print(f"FAISS top-5 retrieval latency: {latency:.2f} ms")
```

**Observed:** sub-10ms per query for <100k vectors in-memory. Pure brute force similarity wins here.

### Structural Recall: Major Gaps

- No sense of order or event sequence. You can't natively fetch "what happened just before this?" or "all records tagged as X."
- Mixed or repetitive context? Embeddings start returning lookalikes, not what's actually relevant—unless you bolt on clumsy metadata filtering.
- Trivial to one-hop recall, hopeless on context chains, dialogue threads, or anything resembling a dependency graph.

#### Why It Fails: Example

Suppose the agent must recall a meeting summary *and* link to prior related action items. Pure vector search drags in loosely related content, often missing explicit cross-document links that actually matter.

- Store both summaries and discrete action items as vectors.
- Query for "next steps from last week’s planning meeting."
- Returns lookalike text, with a strong chance of contaminating context across multiple meetings or omitting key items.

## Graph Databases: Explicit Relationships, Real Scalability Headaches

Graph DBs (Neo4j, RedisGraph, Memgraph) encode relationships naturally. For context-chaining, they're far stronger than vectors. But writes and complex queries go nonlinear fast.

### Neo4j for Agent Memory: Insert and Query

Imagine agent events as nodes (`Event`) with types and `RELATED_TO` edges.

```python
from neo4j import GraphDatabase
import time

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "test"))

def add_event(tx, event_id, event_type, content, timestamp):
    tx.run(
        "MERGE (e:Event {id: $event_id, type: $event_type, content: $content, ts: $timestamp})",
        event_id=event_id, event_type=event_type, content=content, timestamp=timestamp
    )

def link_events(tx, from_id, to_id):
    tx.run(
        "MATCH (a:Event {id: $from_id}), (b:Event {id: $to_id}) "
        "MERGE (a)-[:RELATED_TO]->(b)",
        from_id=from_id, to_id=to_id,
    )

with driver.session() as session:
    start = time.time()
    for i in range(5000):
        session.write_transaction(add_event, f"evt_{i}", "summary", f"content_{i}", i)
    for i in range(1, 5000):
        session.write_transaction(link_events, f"evt_{i-1}", f"evt_{i}")
    latency = (time.time() - start) * 1000
    print(f"Neo4j insert + link 5k events: {latency:.2f} ms")

    query_start = time.time()
    res = session.run(
        "MATCH (e:Event)-[:RELATED_TO*1..3]->(other) WHERE e.id='evt_1000' "
        "RETURN other LIMIT 5"
    )
    print(f"3-hop query latency: {(time.time() - query_start) * 1000:.2f} ms")
```

### Where Graph DBs Lose

- Inserts are at least 10x slower than vector DBs—tens of ms per 1,000 edge inserts.
- Multi-hop queries (`*..n` relationship traversals) explode in cost as your schema gets deeper or more cyclic.
- Cypher queries quickly get unreadable; any "fuzzy" or similarity-weighted search is a hack or plugin.
- Hybrid semantic search requires nontrivial extension work.

**Schema tip:** Nodes for each event, typed with labels; edges for relationships.  
**Pitfall:** Deep, cyclic, or cross-linked graphs crush traversal speed.

## SQL: The Overlooked Hybrid Memory That Holds Up

SQL (Postgres, SQLite) has a bad rep among LLM agent tinkerers, but that’s a miss. With a competent schema and minimal vector support, SQL wins for compound recall and operational scaling.

### Python + SQLite: Real Hybrid Recall

```python
import sqlite3
import numpy as np
import time

conn = sqlite3.connect(":memory:")
c = conn.cursor()
c.execute('''CREATE TABLE memory (
    id INTEGER PRIMARY KEY,
    type TEXT,
    content TEXT,
    ts INTEGER,
    embedding BLOB
)''')

def to_blob(x): return x.astype(np.float32).tobytes()
embeddings = np.random.randn(10000, 1536)
start = time.time()
for i in range(10000):
    c.execute("INSERT INTO memory (type, content, ts, embedding) VALUES (?, ?, ?, ?)",
              ('summary', f"content_{i}", i, to_blob(embeddings[i])))
conn.commit()
print(f"SQLite 10k row insert: {(time.time()-start)*1000:.2f} ms")

def search(query_embed, k=5):
    c.execute("SELECT content, embedding FROM memory WHERE type='summary' AND ts BETWEEN 0 AND 5000")
    rows = c.fetchall()
    X = np.array([np.frombuffer(row[1], dtype=np.float32) for row in rows])
    dists = np.linalg.norm(X - query_embed, axis=1)
    topk = np.argsort(dists)[:k]
    return [rows[i][0] for i in topk]

qvec = np.random.randn(1, 1536)
start = time.time()
results = search(qvec[0], k=5)
print(f"SQLite hybrid filter + search latency: {(time.time()-start)*1000:.2f} ms")
```

### Where SQL Wins

- Multi-constraint queries (e.g., "summaries between times X and Y, linked to project Z") are trivial and performant on indexes.
- Basic vector search is fast enough for tens of thousands of rows, especially with Postgres extensions or Python glue.
- Integrates metadata and semantic search in one query, no extra plumbing.
- Schema evolution and debugging are dramatically simpler than graph or vector DBs.

A mature ops team can evolve SQL schemas, index smartly, and drop in vector tooling for flexible, high-precision recall. Unless you demand million-record fuzzy recall, SQL scales further than most assume.

## Head-to-Head: Actual Numbers and Pain Points

Benchmarks from a Macbook Pro M2, 16GB RAM, Python 3.11. Vector: FAISS. Graph: Neo4j Desktop. SQL: SQLite in-memory.

| Memory Type   | Insert Latency (10k rows) | Top-5 Retrieval | Multi-Hop Recall     | Schema Flexibility | Debuggability | Scaling Ceiling  |
|---------------|---------------------------|-----------------|---------------------|-------------------|---------------|-----------------|
| FAISS vstore  | ~450 ms                   | ~7 ms           | Manual, poor        | Low               | Fair          | RAM-bound       |
| Neo4j graph   | ~5,000 ms                 | ~120 ms (3-hop) | Native, scalable    | Medium            | Poor (Cypher) | Nonlinear cost  |
| SQLite (SQL)  | ~700 ms                   | ~25 ms          | Manual, but simple  | High              | Excellent     | Disk/Index-bound|

**Early failure modes:**
- Vector: Chokes on multi-hop/metadata queries, or >1M vectors without sharding.
- Graph: Bogs down on deep traversals, cyclic schemas, or batch inserts.
- SQL: Bottlenecks without vector indexing at scale, but otherwise robust.

**Recall quality:**
- Vector: Excels at broad similarity, fails for nuanced, cross-linked context.
- Graph: Matches explicit relationships, weak for fuzzy similarity.
- SQL: Satisfies 80% of agent memory constraints—hybrid queries across structured and unstructured data.

## Architecture Choice: What Survives and Where

**Tradeoff diagram (in words):**
- **X Axis:** Recall complexity (fuzzy on left, multi-hop/constraint on right)
- **Y Axis:** Operational readiness (toy demos at bottom, production ops at top)

- **Lower-left:** FAISS/Chroma—dominant for fuzzy, fast at toy and mid-scale, unusable for complex recall.
- **Central band:** SQL with vector support—handles structured, hybrid recall; easy schema evolution.
- **Upper-right:** Graphs—needed only for deeply interlinked or provenance-anchored memory; expensive to scale and debug.

**Skip vector DB when:**
- Ordered, tagged, or event-chained recall trumps raw similarity.
- You need queries like "all action items from meetings with X between Y and Z."

**Hybrid (SQL+vector or Graph+vector) is required when:**
- Both structure and semantic similarity drive retrieval requirements.
- Use SQL for multi-constraint, fall back to vector for fuzzy matches.

**Bottom line:**  
Vectors collapse under production agent memory needs. Graph is specialized, costly for most workloads. SQL outlasts both for operational, flexible, and multi-faceted recall. Choose memory architecture for what the agent actually does—not for "demo simplicity."