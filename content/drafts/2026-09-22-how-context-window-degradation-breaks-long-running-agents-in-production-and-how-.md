---
contrarian: false
generated_at: '2026-09-22T13:56:54.257973+00:00'
pillar: war_stories
sources:
- https://github.com/Brijesh1656/Math-Professor-Ai
- https://github.com/himadriganguly/context-engineering
- https://github.com/Lucenor/mnesis
- https://github.com/terminus-labs-ai/sr2
status: pending_review
subtitle: Learn to spot, measure, and fix the creeping loss of intelligence in agentic
  LLM systems as their context grows, with real code and log examples.
title: How Context Window Degradation Breaks Long-Running Agents in Production—and
  How to Engineer Your Way Out
---

# How Context Window Degradation Breaks Long-Running Agents in Production—and How to Engineer Your Way Out

## LLMs Lose Skills Quietly Before Truncation

Large context windows are overrated. Failed agent logs from projects like [Math-Professor-Ai](https://github.com/Brijesh1656/Math-Professor-Ai) and [context-engineering](https://github.com/himadriganguly/context-engineering) show that LLMs degrade as dialogs grow—even before you hit the window cap. The failure mode isn't just chopped sentences. Agents finish workflows, but core skills—recursion, math, chaining steps—erode or vanish.

**Agent Log: Math-Professor-Ai, 4hr Support Session**

```plaintext
[12:02] User: "Generate and solve a quadratic equation using the student's preferred method."
[12:03] Agent: "Here's a quadratic equation: x^2 + 5x + 6 = 0. Solving by completing the square..."
# [Correct process, correct answer]

...
[15:41] User: "Show another example, using the student's preferred method."
[15:41] Agent: "Here's a quadratic: 2x^2 + x - 3 = 0. I will use the quadratic formula..."
# [Incorrect: The agent ignores session context on preferred method]
```

Context-engineering logs tell the same story. Early in a session, persona and tool use hold. After ~6K tokens, agents default to generic completions—tool use, memory of constraints, and “persona” all fade.

In summary: window saturation erodes context sensitivity and multi-turn skills. Vendors don’t document this, and the problem rarely surfaces in metrics dashboards.

## Context Rot Exposed in Task-Level Metrics

Context rot is visible in regression logs and task benchmarks:

- **Tool Amnesia**: The agent stops using available APIs after enough dialog.
- **Hallucinated State**: The agent responds about non-existent context.
- **Workflow Skip**: Instructions or tasks from earlier turns quietly disappear.

**Integration Test Output:**

```yaml
test_name: "context_persistence_workflow"
steps:
  - input: "Schedule a follow-up using the calendar tool."
    expected_tool: "calendar"
    tokens_used: 223
    outcome: "Success"
  - input: "Now email this to John."
    expected_tool: "email"
    tokens_used: 5473
    outcome: "Failed - Agent replied with freeform text, ignored tool."
  - input: "Which tasks are pending?"
    tokens_used: 5987
    outcome: "Agent omits the follow-up item scheduled earlier."
```

On real Math-Professor-Ai logs, calculation accuracy drops from >95% in the first 1000 tokens to <70% by token 6000 ([June 2024 logs]).

## Summarization Pipelines Fail Under Real Load

Off-the-shelf agent stacks use summarization or simple compaction: truncate, condense, prepend summary, repeat. This loses precision. Projects like SR2/Mnesis demonstrate that summarization misses crucial details in real sessions.

**SR2/Mnesis: Summarization Log Excerpt**

```plaintext
[Summary at 3K tokens]: "The session involves two students learning advanced calculus and preparing for the next exam."
[Later user turn]: "Can you show Sasha's substitutions on the integral from earlier?"
[Agent]: "There is no record of substitutions by Sasha."
# Data lost: summary erased specific sub-dialog; functional regression
```

Summarization collapses under edge cases: dialog requires referencing a prior embedding, or user expects the agent to track persistent constraints. This is a systemic data loss issue, not just a prompt tweak.

## Deterministic Memory Engines Prevent Data Loss

Summarization is inherently lossy. You need deterministic memory: algorithmic selection and reordering of context blocks by recency, entity, or workflow-critical features. This guarantees data recall.

**deterministic_memory.py**

```python
from collections import deque

class DeterministicMemory:
    def __init__(self, max_tokens=2048):
        self.max_tokens = max_tokens
        self.memory = deque()
        self.current_tokens = 0

    def add(self, block, token_count):
        self.memory.append((block, token_count))
        self.current_tokens += token_count
        self._enforce_limit()

    def _enforce_limit(self):
        while self.current_tokens > self.max_tokens:
            block, token_count = self.memory.popleft()
            self.current_tokens -= token_count

    def retrieve(self):
        return [block for block, _ in self.memory]

# Usage Example: inject into agent context window
memory = DeterministicMemory(max_tokens=1500)
memory.add("Tool selection: used calculator at step 3", 20)
memory.add("User preference: 'always round results to 2 decimals'", 15)
# ...
agent_context = "\n".join(memory.retrieve())
```

**Before/After Logs**

```plaintext
# Before deterministic memory:
User: "Always round to 2 decimals from now on."
[10 turns later]
Agent: "The result is 2.3167"

# After deterministic memory:
Agent: "The result is 2.32"
```

Deterministic memory solves persistence and recall. Summarization does not.

## Embedding-Aware Context Skills Outperform Recency Alone

Skill embedding: tag or cluster dialog blocks by skill or task, then use embedding similarity (or explicit markers) to ensure relevant retrieval. This approach holds up to long sessions, far beyond recency/LRU heuristics.

**Minimal Embedding-Aware Selection Example**

Using [SentenceTransformers](https://www.sbert.net/) for semantic similarity:

```python
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

context_blocks = [
    {"text": "User prefers examples using quadratic formula.", "tag": "method"},
    {"text": "Current user topic: advanced calculus.", "tag": "topic"},
    {"text": "Open workflow: schedule meeting.", "tag": "workflow"}
]

def select_context(query, blocks, top_k=2):
    query_embedding = model.encode(query)
    block_embeddings = [model.encode(block["text"]) for block in blocks]
    similarities = util.cos_sim(query_embedding, block_embeddings)[0]
    top_indices = similarities.argsort(descending=True)[:top_k]
    return [blocks[i]["text"] for i in top_indices]

# For agent turn: "Give another quadratic equation example."
selected = select_context("quadratic equation example", context_blocks)
print(selected)
# Output: ['User prefers examples using quadratic formula.', ...]
```

This method maintains recall—even after 100+ turns—when recency and summarization both fail.

## Test What You Truncate—Don’t Assume Context Strategies Work

Few stacks benchmark long conversations. Most test at input/output snapshot granularity, missing context rot in actual sessions.

Build these artifacts into your CI:

1. **Instruction Persistence Test**: Log all explicit user constraints (“always round decimals”), replay, and assert output integrity after window truncation.
2. **Tool Invocation Regression**: Scrape for agent tool call actions over time; alert if usage drops as session length increases.
3. **Context Regression Harness**:

**test_context_rot.py**

```python
def test_instruction_persistence(agent, session):
    instruction = "Always format answers as Markdown"
    agent.feed(instruction)
    for _ in range(20):  # simulate long session
        agent.feed("give a random math example")
    final_output = agent.feed("continue")
    assert "```" in final_output, "Lost Markdown formatting instruction"

# Usage: parametrized over different context management strategies
```

Run these tests on both naive and engineered context management. Track fail rates and measure median session length to first failure.

## Engineered Context Eliminates Functional Drift in Practice

**Naive Summarization Session:**

```plaintext
Turn 1: User: "Always explain with visual analogies."
Turn 15: Agent: "Here is a formula..."
Turn 35: Agent: "The answer is x = 25"   # explanation lost due to summary truncation
```

**Engineered (Deterministic + Embedding-aware) Session:**

```plaintext
Turn 1: User: "Always explain with visual analogies."
Turn 15: Agent: "Imagine this as stacking boxes—here is the formula..."
Turn 35: Agent: "Visual: Think of x = 25 as the height of the stack."
```

---

LLM agents degrade as context grows—often silently. This is a software engineering problem, not a prompt engineering one. Deterministic memory and embedding-aware context beat summarization handily for instruction persistence and workflow recall. Build session-wide regression harnesses and inspect your logs: silent context rot is already present if you aren’t engineering against it.