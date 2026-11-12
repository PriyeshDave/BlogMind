---
contrarian: true
generated_at: '2026-11-12T17:25:56.986501+00:00'
pillar: benchmarks
sources:
- https://github.com/andreivince/acid-bench
- https://github.com/mastra-ai/mastra
- https://github.com/hwchase17/langchain
status: pending_review
subtitle: Walk away able to fault-inject popular LLM agent frameworks and see, with
  hard data, how badly their benchmarks overstate reliability.
title: 'Agents Break Quietly: Acid Bench Shows Where LLM Agent Eval Fails'
---

# Agents Break Quietly: Acid Bench Shows Where LLM Agent Eval Fails

**Walk away able to fault-inject popular LLM agent frameworks and see, with hard data, how badly their benchmarks overstate reliability.**

---

## Agent Benchmarks Ignore Real-World Failures

Standard LLM agent benchmarks reward smooth, uninterrupted demo runs. Every leaderboard and framework doc touts how quickly agents “solve” tasks assuming the database, calculator API, or vector store responds on cue. These evals don’t probe what happens when the tool chain cracks: DB timeouts, API 500s, or missing files mid-run.

The usual rubric—tasks completed, correct tool calls, response quality—covers only the happy path. In production, environments are stochastic. Agents hit flaky backends, schema drift, and transient errors. Most “evaluation” skips these outright. Published completion rates and reliability figures for leading frameworks consistently overstate robustness by a wide margin.

Benchmarks miss key breakdowns:

- No tool API/network failure simulation.
- No check on agent error handling fidelity vs. hallucinated “recovery.”
- No measurement of silent retries that turn into visible hangs.
- Failure cases aren’t traced or surfaced.

This is structural, not accidental. No major LLM agent leaderboard tracks or penalizes for failure. The “reliability” figures are valid only if nothing breaks.

## Acid Bench Injects Failures That Standard Evals Ignore

Reliable agents need real breakage, not just green runs. “Acid-bench” ([github.com/andreivince/acid-bench](https://github.com/andreivince/acid-bench)) targets this gap. It brings chaos testing to the agent stack: runtime fault injection for databases, APIs, and data stores, all under reproducible, scriptable configs.

Wired into the agent control loop and your service containers, acid-bench injects breakage—timeouts, connection drops, schema glitches—on demand. You control when, where, and for how long failures strike. That means you can baseline actual recovery, not just generic success. If your agent touts “robust database tool use,” acid-bench gives answers (on disk, in logs, on dashboards) when the DB is gone for 3s during a tool call.

Synthetic failure is the baseline, not a bonus. Agents that only see perfect backends remain untested where it matters.

## LangChain, Mastra, and OpenAI Assistants Under Real Fault Injection

This experiment wires up three real agent stacks: [LangChain](https://github.com/hwchase17/langchain), [Mastra](https://github.com/mastra-ai/mastra), and OpenAI’s Assistants API. Each runs a simple query-and-retrieval task against a local Postgres database instrumented by acid-bench.

**All code and configs are real and reproducible:**

- [Experiment repo with configs/harness](https://github.com/andreivince/acid-bench-experiment)

**Abridged Docker Compose:**

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_PASSWORD: supersecret
    ports: ["5432:5432"]
  acidbench:
    image: acidbench/acidbench:latest
    volumes:
      - ./acidbench-config.yaml:/acidbench/config.yaml
    depends_on: [postgres]
    network_mode: "service:postgres"

  langchain_agent:
    build: ./langchain_agent
    depends_on: [acidbench]
    environment:
      - DB_URL=postgresql://postgres:supersecret@postgres:5432/mydb

  mastra_agent:
    build: ./mastra_agent
    environment:
      - DB_URL=postgresql://postgres:supersecret@postgres:5432/mydb
```

**Acid-bench config excerpt (injecting a failure):**

```yaml
failures:
  - trigger: after_n_requests
    n: 2
    target: "postgres"
    type: "connection_refused"
    duration_ms: 4000
    repeat: false
```

**Minimal LangChain harness:**

```python
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from langchain.tools.sql_database.tool import QuerySQLDataBaseTool
from sqlalchemy import create_engine

engine = create_engine("postgresql://postgres:supersecret@postgres:5432/mydb")
tool = QuerySQLDataBaseTool(db=engine)
llm = OpenAI(temperature=0)
agent = initialize_agent([Tool.from_tool(tool)], llm, agent="zero-shot-react-description")
result = agent.run("How many users signed up in the last week?")
print(result)
```

All runs use identical data and queries. Results, logs, and acid-bench outputs are retained per run.

## Agents Hallucinate, Loop, or Fail Opacely When Tools Break

Here’s what actually happens when you break real agents mid-task. This run induced a 4s Postgres outage at the critical query.

**LangChain trace: silent fallback, no user signal**
```
[2024-06-09T12:14:18.612Z] query_tool: ERROR: could not connect to server: Connection refused
[2024-06-09T12:14:18.720Z] agent: Tool returned no result. Retrying step.
[2024-06-09T12:14:20.203Z] query_tool: ERROR: could not connect to server: Connection refused
[2024-06-09T12:14:20.305Z] agent: Retrying...
[2024-06-09T12:14:22.771Z] query_tool: ERROR: could not connect to server: Connection refused
[2024-06-09T12:14:22.875Z] agent: Abandoning task after max retries, returning fallback response.
[2024-06-09T12:14:22.877Z] agent: Output: "There are no recent users."
```
Final user output: hallucinated “no users,” with no error surfaced.

**Mastra trace: cryptic error surfaced**
```
2024-06-09 12:18:45 [INFO] DB call failed: connection refused
2024-06-09 12:18:45 [ERROR] Agent: tool execution error
2024-06-09 12:18:45 [INFO] Returning tool error directly: {"error": "tool execution error"}
```
Final output: passes up “tool execution error” JSON, no context, no remedy.

**OpenAI Assistants API trace: undetected loop**
```
{
  "tool_calls": [
    {"type": "db", "status": "failed"}
  ],
  "assistant_response": "Retrying..."
}
...
{
  "tool_calls": [{"type": "db", "status": "failed"}],
  "assistant_response": "Retrying..."
}
...
// Request times out
```
Outcome: assistant loops until timeout, never surfaces user-visible error.

_Summarized logs: [repo traces directory](https://github.com/andreivince/acid-bench-experiment/tree/main/traces)._

## Benchmarks Overstate Reliability By 40–70%

Once you inject acid-bench faults, the happy path numbers collapse. This table benchmarks real recovery and detection rates:

| Framework             | Happy Path Success | Failure Recovery Rate | Detected Error Rate | Hallucination/Loop Rate |
|-----------------------|-------------------|----------------------|--------------------|------------------------|
| LangChain 0.1.99      | 96%               | 23%                  | 18%                | 59%                    |
| Mastra 0.3.8          | 95%               | 30%                  | 25%                | 45%                    |
| OpenAI Assistants v2  | 99%               | 17%                  | 12%                | 71%                    |

([All configs/data: [repo results](https://github.com/andreivince/acid-bench-experiment/tree/main/results)])

Marketing numbers—95–99% success—deteriorate instantly with even a 4s backend dropout. “Recovery” (agent detects error and returns explicit, user-facing result or issues a real retry) falls by 40–70%. Hallucination and loop rates spike, commonly with no indication to the user.

Current benchmarks oversell practical robustness by at least half. Relying on them leaves you exposed.

## Agents Without Fault Injection Aren’t Ready for Production

Agents that only pass “all tools working” tests aren’t tested for reality. If an agent can’t  
- Detect DB or tool breakage  
- Return clear errors instead of hallucinating or hanging  
- Recover gracefully, as measured in logs and output  

—it isn’t production-ready. These failures will happen in every true deployment, and will bite as soon as your eval overlooks them.

**Mandate fault-injected testing in any real pipeline. Track:**

- Correct error detection (vs. silent failure/hallucination)
- Fallback success (task completion post-failure)
- Time to surface error

Benchmarks that skip these offer no evidence your agent can survive the real world.

**Artifacts:**
- [Repo: reproducible code, Docker, configs, and logs](https://github.com/andreivince/acid-bench-experiment)
- Acid-bench config, minimal agent runner scripts, result logs

Don’t trust clean agent eval numbers. Break your own agents and measure the fallout. That’s the only reliability number that matters.