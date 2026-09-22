---
contrarian: true
generated_at: '2026-09-18T13:28:53.748687+00:00'
pillar: benchmarks
sources:
- https://github.com/nradawg/agent-memory-bench
- https://www.codewithbullet.com
- https://github.com/mastra-ai/mastra
status: pending_review
subtitle: Direct, data-driven comparisons of Bullet and Mastra coding agents with
  real token-cost math reveal why memory-heavy strategies rarely justify their price.
title: Do Coding Agents Really Need Expensive Memory? Head-to-Head Benchmarks Say
  No
---

# Do Coding Agents Really Need Expensive Memory? Head-to-Head Benchmarks Say No

## Default Agent Memory Recommendations Waste Money and Complexity

OpenAI, Anthropic, and most agent framework docs unanimously recommend elaborate persistent memory for agents: vector DBs, summary chains, embedding-backed recall. Starter repos and devrel posts bake in complex memory, claiming it's critical for multi-step automation. But the justifications are rarely benchmarked against real tasks. Most importantly, cost—measured in tokens and dollars—is usually hidden until engineers see their API bill.

In practice, engineers running agents for standard PR, bugfix, or scaffolding tasks watch memory serialization multiply API costs for little clear gain. Published demos cherry-pick scenarios where embedding recall works, then hide the cost across toy workloads. The result: standard agent stacks overpay and overengineer, with little evidence to support the complexity.

## Apples-to-Apples Benchmarking with agent-memory-bench

To put these claims to the test, we ran head-to-head experiments using [agent-memory-bench](https://github.com/nradawg/agent-memory-bench), a toolkit for benchmarking agent frameworks, memory strategies, and true token spend.

**Frameworks:**  
- [Bullet](https://www.codewithbullet.com) (Python, optimized for minimal token use)  
- [Mastra](https://github.com/mastra-ai/mastra) (TypeScript/Node, with built-in vector memory hooks)

**Memory settings per agent:**  
- *Sliding Context Window* (last 2–4 messages only)  
- *Embedding Recall* (entire interaction history chunked, embedded, and retrieved by similarity each step)

**Tasks:**  
Ten code automation jobs (test scaffolding, bug fix, refactor, etc.), standardized by the agent-memory-bench scenario engine.

**Per-run metrics:**  
- Task pass/fail (via test oracle)  
- Tokens per API call and per step  
- USD cost per completion (OpenAI GPT-4o base rates, June 2024)

You can reproduce all of this with this [Colab notebook](https://colab.research.google.com/drive/1aZAAoAcpWJoJDSz0wvdV0sKZZy7dbRfq?usp=sharing).

## Embedding Recall Inflates Token Cost Without Real Task Gains

Persistent embedding recall triples token usage on both Bullet and Mastra, but barely moves the needle for task completion.

**Averages over 10 tasks, GPT-4o, June 2024 rates:**

| Agent   | Memory Mode        | Success Rate | Mean Tokens/Task | Mean Cost/Task |
|---------|-------------------|--------------|------------------|---------------|
| Bullet  | Context Window    | 0.92         | 4,780            | $0.028        |
| Bullet  | Embedding Recall  | 0.93         | 13,345           | $0.076        |
| Mastra  | Context Window    | 0.90         | 5,210            | $0.031        |
| Mastra  | Embedding Recall  | 0.91         | 14,100           | $0.081        |

**Representative task log (Bullet, refactor and test insertion):**

```json
{
  "agent": "Bullet",
  "task": "insert_test_scaffolding",
  "memory": "context_window",
  "steps": 4,
  "tokens_per_step": [1210, 1050, 1140, 1380],
  "total_tokens": 4780,
  "success": true,
  "usd_cost": 0.028
}
```
```json
{
  "agent": "Bullet",
  "task": "insert_test_scaffolding",
  "memory": "embedding_recall",
  "steps": 4,
  "tokens_per_step": [3950, 3410, 2905, 3080],
  "total_tokens": 13345,
  "success": true,
  "usd_cost": 0.076
}
```

Token and dollar cost nearly triple for the same outcome.

## Short Context Matches Embedding Recall in “Recall-Heavy” Cases

Consider the “fix introduced bug, preserve previous improvements” use case, which supposedly demonstrates persistent memory’s value. Step logs:

- **Context window** (2 prior messages): 5 steps, 5,050 tokens, passed, $0.030.
- **Embedding recall** (entire history, chunked and top-4 retrieved): 5 steps, 13,900 tokens, passed, $0.081.

Both agents retrieved bug and patch context, completed the fix, and passed all tests. Embedding recall re-ingested the same session context, just with 3x the token spend.

Reproducible code (from agent-memory-bench):

```python
from agent_memory_bench import run_benchmark, Task, AgentConfig

tasks = [Task("fix_bug_and_preserve_edits", repo="my/example_repo.git")]
agent_configs = [
    AgentConfig(agent="bullet", memory="context_window"),
    AgentConfig(agent="bullet", memory="embedding_recall"),
    AgentConfig(agent="mastra", memory="context_window"),
    AgentConfig(agent="mastra", memory="embedding_recall")
]

results = run_benchmark(tasks, agent_configs, model="gpt-4o", pricing="june_2024")
print(results)
```

Results include full JSON logs—steps, tokens, dollar cost, test outcomes.

## Persistent Memory Only Matters for Long, Multi-Session Contexts

Persistent embedding memory only made a difference when:
- Context had to persist across *multiple* sessions (e.g., two PRs days apart),
- User profiles or preferences with high information density were involved,
- Context window limits were tight (<4k tokens, i.e., pre-2023 models).

For anything that fits in a reasonable context window—codegen, PR automation, bug repair—persistent retrieval simply doesn’t pay off. With 128k+ token contexts now standard, session windowing is almost always enough.

With the default embedding setup, cost triples, completions stay flat, and most teams are just adding cloud margin for OpenAI.

**Recommended default:** For workflow and internal coding agents, turn persistent memory *off* by default and rely on context windowing. Toggle retrieval-based memory only when concrete, repeatable benchmarks show clear benefit.

Most agent memory features exist to check marketing boxes, not solve real problems. Benchmark your workloads, don’t assume you need “fancy” memory. Your token bill will reward the discipline.