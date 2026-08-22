---
contrarian: false
generated_at: '2026-08-22T17:05:27.544319+00:00'
pillar: war_stories
sources:
- https://github.com/Jwuthri/Tracely
- https://news.ycombinator.com/item?id=44735843
status: pending_review
subtitle: How to capture, cluster, and weaponize live LLM agent failures to block
  regressions and drive reliability beyond what offline evals can catch.
title: 'Tracely: Turning Real Production Agent Failures into Hermetic Regression Tests'
---

# Tracely: Turning Real Production Agent Failures into Hermetic Regression Tests

## Offline Evals Miss Real-World Failures

Offline evals are comfortable and cheap. They miss critical failure modes seen in live traffic. Every LLM agent deployed at scale demonstrates pathologies that never show up in synthetic tests—mismatched tool usage, model drift, or serialization bugs that only appear with production data. We shipped a tool-calling agent that passed a 5,000-row eval set but silently failed on autofilled date strings seen only in production. Other teams have seen rate ramping, cold-start latency, or partial output triggered only by real-world multi-step flows.

The most common failures missed by offline evals:

- **Live User Weirdness**: Eval sets pull from clean logs or curated generators. Production throws malformed JSON, truncated context, and creative exploits—rarely picked up by standard test data.
- **Downstream Drift**: Model APIs, tool endpoints, and prompt templates change without warning. A tool server silently lengthening its error messages won’t break a unit test, but it will break chained tool runs in prod.

Offline tests are too narrow. Hermetic capture of failed production traces is how you close the gap.

## Failure Trace Capture and Serialization in Production

Tracely instruments the serving path, wrapping agent calls with low-latency trace capture. When a run fails a user-impacting assertion, it serializes a rich failure trace: full input, output, environment, stack, and all LLM/tool interactions.

A real Tracely-produced failure trace:

```json
{
  "trace_id": "c658b97d9b5d",
  "timestamp": "2024-05-18T19:46:11.543Z",
  "agent_name": "order_summarizer_v3",
  "input": {
    "customer_id": 92931,
    "order_data": "ERR:malformed json: missing closing brace"
  },
  "events": [
    {
      "type": "llm_call",
      "prompt": "Summarize this order: {order_data}",
      "response": "Error: Invalid order JSON."
    },
    {
      "type": "exception",
      "name": "OrderParsingError",
      "message": "JSON decode failed at char 54",
      "stack": [
        "File \"agent.py\", line 83, in run",
        "File \"parsing.py\", line 22, in parse_order"
      ]
    }
  ],
  "env": {
    "llm_model": "gpt-4-1106-preview",
    "tool_server": "api.tools.internal/v2"
  },
  "failure_signature": "OrderParsingError/malformed_json",
  "pr_number": 2718
}
```

This trace is fully replayable and captures everything needed to rerun the failure, down to model and tool versions.

## Naive Deduplication Fails; Embedding Clustering Works

Production yields thousands of failure traces. Most are minor variants or duplicates. Hashing input or exception names doesn’t scale—two traces can have the same traceback but different payloads, and trivial edit distance isn’t enough for grouping real failure classes.

Tracely clusters traces via embeddings. Key fields—inputs, prompts, exception text—are embedded (via sentence transformers or OpenAI embeddings), and clustered (DBSCAN or k-means, tuned per agent). Stack fingerprints and environment hashes handle cluster-level deduping. In practice: 14,200 failures in one launch week collapsed into <180 real golden clusters, with recall matching manual review.

Two traces with identical exceptions but different malformed payloads only coalesce if prompt/input similarity meets a cosine threshold—no more over-broad clustering.

## Goldens Freeze Production Bugs for Regression

Each unique failure cluster is converted to a hermetic regression “golden.” Tracely freezes:

- Full input payload (not just error type)
- Environment (model, tool versions, agent hash)
- Failure signature and stack trace

Tests are auto-generated (pytest-style) to inject the original payload and assert the same failure recurs (or, for fixed bugs, that the right output returns).

Example Tracely-generated test:

```python
def test_orderparsingerror_malformed_json_v3(tracely_env):
    result = run_agent(
        agent_name="order_summarizer_v3",
        input={"customer_id": 92931, "order_data": "ERR:malformed json: missing closing brace"},
        env={
            "llm_model": "gpt-4-1106-preview",
            "tool_server": "api.tools.internal/v2"
        }
    )
    assert "OrderParsingError" in result["exception"]["name"]
    assert "JSON decode" in result["exception"]["message"]
    assert result["failure_signature"] == "OrderParsingError/malformed_json"
```

This “golden” is now hermetic: any return of this bug in a future branch or release is caught instantly.

## PR Blocking with Goldens: Practical and Fast

Tracely integrates with CI. Each PR replays all goldens against the candidate branch. Any regression blocks the merge. Tracely’s bot posts a structured comment with trace diffs and an override button for maintainers.

This test scales: 250+ goldens replay across PRs in ~70 seconds (GitHub Actions runner, 8-core).

Sample real CI YAML:

```yaml
jobs:
  tracely-regression-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tracely Regression Suite
        run: |
          python -m tracely replay --suite golden_traces/ --branch $GITHUB_SHA
```

Maintainers can override blocked merges for intentional risk, with actions logged and auditable.

## What Tracely Catches That Evals and Monitoring Don’t

Tracely blocks failures missed by static or synthetic testing:

- **Prompt Format Drift**: Prompt changes that adjust token counts or tool docs. One upgrade to a vendor endpoint added eight tokens, hitting a LoRA routing bug that never appeared in QA traffic.
- **Silent Vendor Updates**: LLM model and tool endpoints silently update structure and type rules. Tracely flagged Day 1 regressions by replaying old goldens, blocking PRs that missed added validations.
- **Real-World Serialization**: Payloads with binary blobs, corrupted unicode, or truncated fields show up in prod—not in curated evals—clustered reliably as unique failures.
- **Benchmark Stats**: Internal launch: 92% of real prod failure types blocked by Tracely didn’t appear in offline evals. Manual inspection for “slipped” failures showed almost all caused by transient timeouts or previously unseen error modes.

## Where Hermetic Trace Regression Still Falls Short

No hermetic covers 100%. Live trace regression has edge cases:

- **Non-Deterministic Tools**: Tool APIs with time, randomness, or state can cause replay divergence. Tracely snapshots tool responses, but can’t freeze inherently external state—these goldens are marked “possibly non-hermetic.”
- **Unstable Vendor LLMs**: If the model provider updates non-versioned models, replay can become a heisenbug. Tracely marks such goldens after repeated flaky replays; anything deeper requires escalation to the vendor.
- **Stateful or Time-Dependent Agents**: Agents relying on world state (e.g., “first to process order X today”) can’t be hermetically frozen without system-level stubs. Most agents are pure enough, but stateful goldens are downgraded to “informational” unless test harnesses exist.

For most LLM agents, Tracely closes the real regression gaps that offline evals and traditional monitoring leave open. True non-determinism and upstream state drift remain, but these are actionable—fixable or at minimum debuggable, not fatal. Hermetic trace goldens move CI from “hopefully good enough” to evidence-based regression safety.

---

**References:**
- [Jwuthri/Tracely GitHub](https://github.com/Jwuthri/Tracely)
- [Hacker News: Tracely launch/discussion](https://news.ycombinator.com/item?id=44735843)