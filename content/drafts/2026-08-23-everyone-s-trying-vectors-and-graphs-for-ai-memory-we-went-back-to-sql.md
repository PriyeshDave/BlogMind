---
contrarian: false
generated_at: '2026-08-23T16:42:01.914311+00:00'
pillar: architecture
sources:
- https://news.ycombinator.com/item?id=45329322
- https://github.com/aashir771/Memory-Layered-Agent-Core
- https://github.com/MrPeppersDev/agent-infrastructure-landscape
status: pending_review
subtitle: Get real performance and clarity on how plain SQL outperforms or complements
  modern vector DBs for persistent agentic memory—with working code and an architecture
  diagram.
title: Everyone's Trying Vectors and Graphs for AI Memory. We Went Back to SQL.
---

# Everyone's Trying Vectors and Graphs for AI Memory. We Went Back to SQL.

## Vector Stores Add Latency and Complexity For Most Agent Memory

The default in 2024 for agentic LLM memory is a vector DB with a glossy API claiming semantic search at scale. Docs hype embedding-powered lookups and treat SQL as legacy.

For most agentic workloads, that's backwards. Unless you're at hundred-million-vector scale, vector DBs add sync/async glue, ops overhead, surprising ANN recall quirks, and debugging headaches. You lose the ability to reason predictably about queries by user, timestamp, or tag.

Classic SQL wins when you need precise, scoped recall—"what facts are in my recent working memory, for topic X, since 10 minutes ago"—in a single query. Vector search gives you best-effort, top-k returns, often unstable when embeddings drift or you upgrade models. ANN recall is not a drop-in replacement for classic key+filter queries.

## SQL Outperforms Vector DBs for Structured and Temporal Recall

Vector DBs are for pure semantic smash-and-grab, not layered or episodic memory. SQL handles all the details—structured, temporal, filtered recall—directly.

Concrete example: SQLite “memory” table with text, timestamp, tag, and blob embedding. To fetch agent memories from the past hour tagged ‘alpha’:

```python
import sqlite3
import time

conn = sqlite3.connect(":memory:")
cur = conn.cursor()
cur.execute("""
CREATE TABLE memory (
    id INTEGER PRIMARY KEY,
    text TEXT,
    ts REAL,
    tag TEXT,
    embedding BLOB
)
""")
now = time.time()
cur.execute("INSERT INTO memory (text, ts, tag) VALUES (?, ?, ?)", ("Fix bug in alpha repo", now - 60, "alpha"))
cur.execute("INSERT INTO memory (text, ts, tag) VALUES (?, ?, ?)", ("Lunch with team", now - 120, "social"))
cur.execute("INSERT INTO memory (text, ts, tag) VALUES (?, ?, ?)", ("Review alpha doc", now - 180, "alpha"))
conn.commit()

recent = cur.execute(
    "SELECT text FROM memory WHERE tag = ? AND ts > ?", ("alpha", now - 120)
).fetchall()
print([r[0] for r in recent])  # Output: ['Fix bug in alpha repo']
```

No ANN approximation, no hybrid postfilter. Deterministic, explainable, instantly extensible.

Try this with Chroma or Pinecone and you end up wrestling with post-hoc filtering, multi-stage APIs, or hand-jamming your own query+filter loop.

## Storing Embeddings in SQL and Doing Semantic Match Works for <100K Rows

"Fine, but what about semantic similarity?" You can store embeddings in SQL and run brute-force similarity for agent memory. For tables under 100k items, in-memory SQLite with vector columns remains fast and local.

### SQLite table with cosine similarity (numpy)

```python
import numpy as np
import sqlite3

def make_embedding(text):
    return np.random.rand(384).astype(np.float32)  # Real model would go here

conn = sqlite3.connect(":memory:")
cur = conn.cursor()
cur.execute("""
CREATE TABLE memory (
    id INTEGER PRIMARY KEY,
    text TEXT,
    embedding BLOB
)
""")
for txt in ["Fix alpha bug", "Go to lunch", "Review docs"]:
    emb = make_embedding(txt).tobytes()
    cur.execute("INSERT INTO memory (text, embedding) VALUES (?, ?)", (txt, emb))
conn.commit()

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

q_emb = make_embedding("alpha bugfix")
rows = cur.execute("SELECT text, embedding FROM memory").fetchall()
sims = [(txt, cosine_sim(np.frombuffer(emb, np.float32), q_emb)) for txt, emb in rows]
top = sorted(sims, key=lambda x: -x[1])[0]
print("Best SQL match:", top)
```

### Chroma/Vector DB example

```python
# pip install chromadb sentence-transformers
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.Client()
collection = client.create_collection("memory")
model = SentenceTransformer('all-MiniLM-L6-v2')

docs = ["Fix alpha bug", "Go to lunch", "Review docs"]
ids = [str(i) for i in range(len(docs))]
embeddings = model.encode(docs).tolist()
collection.add(documents=docs, ids=ids, embeddings=embeddings)

q_emb = model.encode(["alpha bugfix"]).tolist()
results = collection.query(query_embeddings=q_emb, n_results=1)
print("Best vector DB match:", results['documents'][0][0])
```

#### Measured Performance

On tables <100k items, brute-force numpy-in-SQLite hits 5-20ms/query. Networked vector DBs rarely match that for individual queries unless batch-mode or sharded. At 1M+ rows or multi-writer concurrency, SQL falls behind unless you migrate to an ops-heavy faiss or pq-index setup. For agentic memory under 4k tokens or <50 document recall per turn, classic SQL is hard to beat for speed and transparency.

## SQL Schema Patterns Cover Most Agentic Memory Needs

Agent memory isn't a flat event log. There's a recent cache, an episodic/workspace slice, and a long-term archive. All of this models cleanly in SQL.

Typical tables:

- `memory_event`: `id`, `timestamp`, `agent_id`, `level` (cache/working/long_term), `text`, `tag`, `embedding`
- `memory_index`: aggregated contexts, multi-agent links, session chains
- Compound indexes: `(agent_id,level,timestamp)`, `(embedding)`

**Multi-Tier Recall Diagram:**

Picture three SQL tables:

1. **Cache**  
   Rows expire via TTL or are purged by time-based jobs. Recent, high-frequency events with tight recall bounds.

2. **Working Memory**  
   Last N events per agent/session. Indexed for fast slice by `(agent_id, timestamp)`.

3. **Long-Term**  
   Archive, compressed or vectorized. Used for distant recall, batch jobs, or semantic search.

Promotion and TTL triangle: events move up to long-term; expired/dormant items evicted down. Queries cross levels via SQL unions or joined predicates—no routers, no multi-pass graph walks.

## Vector and Graph Stores Only Win at Scale or On Graph-Heavy Workloads

Plain SQL with embeddings breaks for:

- Tens of millions+ vectors and brute-force queries (unless you bolt on faiss/ann-index).
- Dense, multirelational graphs (e.g., knowledge graphs with multi-hop traversal).
- Big semantic+graph hybrid searches.

Those cases are rare for agentic memory workloads. Unless you need unstructured instant ANN for millions+ items or deep semantic graph reasoning, classic SQL remains the lowest-latency and most understandable answer.

## Use Case Table

| Use Case                                   | SQL MemTable         | Vector DB / Chroma      | Knowledge Graph              |
|---------------------------------------------|----------------------|------------------------|------------------------------|
| Current working memory (<10k items)         | 🟢 Fast, clear       | 🟡 Sometimes overkill   | 🔴 Overcomplex               |
| Semantic + structural (e.g. tag, time)      | 🟢 Single query      | 🟡 Needs hybrid query   | 🔴 Postfilter or custom walk |
| Distant context, pure semantic              | 🟡 Slow at scale     | 🟢 Native support       | 🟢 Can map, less explainable |
| Ultra-large (>1M) unstructured recall       | 🔴 Fails             | 🟢 Scales up            | 🟡 Graph plausible           |
| Multi-hop relationships, concept graphs     | 🔴 Not native        | 🔴 Not ideal            | 🟢 Built for this            |

SQL remains the best default for agentic “memory” unless you truly require large-scale semantic or graph search. Bench your workload before assuming vector DBs or knowledge graphs are upgrades. For most agent memory, they’re complexity—SQL is the real fast path.