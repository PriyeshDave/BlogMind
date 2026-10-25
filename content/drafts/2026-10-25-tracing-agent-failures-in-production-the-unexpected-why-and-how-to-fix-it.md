---
contrarian: false
generated_at: '2026-10-25T13:36:36.790466+00:00'
pillar: war_stories
sources:
- https://github.com/sarkars/agent-failure-modes
- https://github.com/onTracify/Tracify
status: pending_review
subtitle: You’ll see actionable trace instrumentation, concrete failure case studies,
  and tools for root-causing agent bugs that only surface after deployment.
title: 'Tracing Agent Failures in Production: The Unexpected Why and How to Fix It'
---

# Tracing Agent Failures in Production: The Unexpected Why and How to Fix It

**Subtitle:** Actionable trace instrumentation, real-world failure data, and tools for isolating agent bugs that only surface after deployment.

## Synthetic Eval Misses Most Production Failures

Agent failures that matter show up only in production. Synthetic evals—even with noisy contexts or simulated user drift—miss entire classes of failure. [sarkars/agent-failure-modes](https://github.com/sarkars/agent-failure-modes) catalogs failure types missed by evals: infinite tool loops, runaway chains from odd prompt tails, and latency blowups from retry policies misfiring. Multiple production LLM agents passed every OpenAI Eval and then soft-locked day one against input distributions absent from QA.

A direct data point: [onTracify/Tracify](https://github.com/onTracify/Tracify) engineers audited a new RAG agent’s first 48 hours in production logs. They found *eleven* step loops or excessive latency incidents—none reproduced by QA or lab evals. Fake traffic, no matter how adversarial, isn’t real.

## Traces Reveal Root Cause, Not Just Surface Symptoms

Raw error logs show timeouts, 422s, and assertion failures. Tracing surfaces the actual reasoning chain and sequence of tool use, revealing how failures develop. Both sarkars/agent-failure-modes and Tracify’s public writeups make this clear:

```text
# Excerpt from a real trace (anonymized):
[2024-05-19T23:40:07Z] LLM step: "Check product inventory for SKU 1234"
[2024-05-19T23:40:08Z] Tool: inventory.check(1234) -> Out of Stock
[2024-05-19T23:40:09Z] LLM step: "Re-check product inventory for SKU 1234"
[2024-05-19T23:40:10Z] Tool: inventory.check(1234) -> Out of Stock
[2024-05-19T23:40:11Z] LLM step: "Try again: check inventory for SKU 1234"
...
```
This trace shows a live loop. Each step looks sane in isolation, but only tracing reveals the circular failure. Standard logs show perfectly acceptable tool calls—not the underlying dead-end reasoning.

## Tool Choice Loops Hide in Self-consistent Traces

Agents that look robust in evals can loop forever on tool selection once deployed. [sarkars/agent-failure-modes](https://github.com/sarkars/agent-failure-modes#tool-choice-loops) documents traces where, under rare context mismatches, the agent enters a plausible but endless chain of tool invocations. Single-step logs miss this infinite regress entirely.

### Example: Infinite Tool Loop Trace

```text
[user]: "Is store X open right now?"
[agent, step 1]: Use tool: get_store_hours(X)
[result]: "Open until 9PM"
[agent, step 2]: Use tool: get_current_local_time(X)
[result]: "8:45PM"
[agent, step 3]: Use tool: get_store_hours(X)
[result]: "Open until 9PM"
[agent, step 4]: Use tool: get_current_local_time(X)
[result]: "8:46PM"
# And on...
```

Each step appears locally logical. Only the full trace shows the pointless oscillation. Synthetic test prompts rarely create the time zone ambiguity and phrasing mix that triggers this in the wild.

## Latency Spirals from Invisible Retries

Retries are often invisible unless explicitly instrumented. [onTracify/Tracify](https://github.com/onTracify/Tracify/issues/12) details a real case: customers saw sporadic multi-minute waits, but logs showed only one or two retries per call. Only production traces exposed the real sequence:

```text
[trace_id=abc-123]
[2024-05-21T07:01:00Z] Tool call: fetch_item_details(id=42)
[2024-05-21T07:01:05Z] Timeout, retry 1
[2024-05-21T07:01:10Z] Timeout, retry 2
[2024-05-21T07:01:15Z] Timeout, escalate to fallback tool
[2024-05-21T07:01:20Z] Fallback tool triggers additional retries due to 429s
[2024-05-21T07:01:30Z] Final fallback returns failure
# Total latency: 30s+
```

No single component violated retry or timeout policy. The stacking of retry logic across layers was visible only in the cross-cutting trace, which explained the real cause of latency spikes.

## Instrumentation: What You Actually Need for Production Traces

Real root-causing demands trace coverage for every agent step, tool call, and API result. Tracify ships a ready tracer, but most agent stacks can add trace instrumentation with lightweight wrappers.

Minimum requirements: per-request trace IDs, child spans for every reasoning step, per-step timing, capture of all "thoughts," and every tool invocation.

### Minimal Trace Wrapper (Actual Code)

```python
import uuid
import time
import functools

class Trace:
    def __init__(self, trace_id=None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.events = []

    def log(self, step, detail, meta=None):
        self.events.append({
            'timestamp': time.time(),
            'step': step,
            'detail': detail,
            'meta': meta or {}
        })

def trace_agent_step(trace, step_name):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.time()
            try:
                result = fn(*args, **kwargs)
                trace.log(step_name, f"Completed: {fn.__name__}",
                          {'duration': time.time() - t0,
                           'result': str(result)[:300]})
                return result
            except Exception as e:
                trace.log(step_name, f"Error in {fn.__name__}",
                          {'duration': time.time() - t0,
                           'error': repr(e)})
                raise
        return wrapper
    return decorator

# Usage in agent
trace = Trace()
@trace_agent_step(trace, step_name="LLM Reasoning")
def agent_reasoning_step(context):
    # actual LLM reasoning code here
    return "Next action: use_tool('lookup_user')"

@trace_agent_step(trace, step_name="Tool Invocation")
def invoke_tool(tool_name, *args):
    # simulate tool API call
    time.sleep(0.2)
    return {"ok": True, "data": 123}

# Example run
out = agent_reasoning_step("prev context")
tool_out = invoke_tool('lookup_user', 42)
# At any point:
print(trace.events)
```

Tracify’s full implementation is OpenTelemetry-compatible, but the minimal pattern above is enough to capture and reproduce key production failure cases.

## Fixes Unlocked by Tracing: Guardrails and Budget Enforcement

Traces enable root-level mitigation, not workarounds. For the infinite tool loop, a simple `max_steps` ceiling stopped degenerate rollouts, and adding a pattern detector cut off oscillating multi-tool loops:

```python
class LoopDetector:
    def __init__(self, max_repeats=3):
        self.history = []
        self.max_repeats = max_repeats

    def check(self, action):
        self.history.append(action)
        if self.history[-self.max_repeats:] == [action] * self.max_repeats:
            raise RuntimeError(f"Detected {self.max_repeats} repeats of {action}")

detector = LoopDetector()
for act in agent_action_sequence:
    detector.check(act)
    # run act...
```

For latency spirals, traces showed that fallback retries stacked atop base timeouts. The fix: each agent request now enforces a *total* retry and latency ceiling, not just per-call caps. This change eliminated tail latency incidents in production.

```python
TOTAL_BUDGET_SEC = 20
start = time.time()
retries = 0
while (time.time() - start) < TOTAL_BUDGET_SEC:
    try:
        result = tool_call(...)
        if result['ok']:
            break
    except SomeToolException:
        retries += 1
        continue
else:
    # hit overall budget cap
    logger.error(f"Aborted after {retries} retries and {TOTAL_BUDGET_SEC} seconds")
```

## Logging Outputs and Exceptions Is Not Enough

Logging agent outputs and errors will not identify or fix the failures that matter. Only traces—full reasoning chains, every tool call, step timings, and user input—provide enough context for real root cause analysis. This is the only proven way to catch infinite loops, retry spirals, and context-sensitive bugs *before* they destroy uptime and trust. Retrofitting basic trace instrumentation is trivial compared to the potential chaos and downtime. Every agent in production should emit traces, and every on-call should know how to read them. This separates trivial demos from agents ready for real risk and scale.