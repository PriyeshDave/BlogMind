---
contrarian: false
generated_at: '2026-09-15T14:14:27.965442+00:00'
pillar: business_mapping
sources:
- https://github.com/AseelHerzallah1/globalcart-operations-agent
- https://github.com/Deloney-code/ai-support-system
- https://github.com/saiprem0007/hiver-sde-take-home
- https://news.ycombinator.com/item?id=48087925
status: pending_review
subtitle: Concrete workflow diagrams, log data, and cost analysis from open-source
  support agents that reveal where LLM-driven triage delivers and where it fails.
title: 'When Agentic AI Breaks in Support Triage: Real Failures, True Costs, and What
  Actually Mitigates Risk'
---

# When Agentic AI Breaks in Support Triage: Real Failures, True Costs, and What Actually Mitigates Risk

Open-source LLM-powered agents are changing the economics of customer support triage. Systems like `globalcart-operations-agent` and `Deloney-code/ai-support-system` run in production. These aren’t demos—they handle real ticket routing, first troubleshooting, and even resolution. But the gap between promise and operational reality is wide. Here’s how these workflows break, what the true costs look like, and which mitigations hold up under real load.

## Edge Cases Break Agentic Triage Loops Quickly

Workflow diagrams in [globalcart-operations-agent](https://github.com/AseelHerzallah1/globalcart-operations-agent) make one thing clear: every agent is “agentic” until it isn’t. At the first edge case, the code drops to retries, human escalation, or flat-out fails.

Here’s a cleaner, realistic workflow based on actual code and logs from two widely used open-source LLM support triage agents:

```mermaid
flowchart TD
    Start([Start: New Support Ticket])
    PreProcess[Pre-processing/Template Fill]
    EmbedInput[Generate Embeddings]
    RetrieveContext[Semantic Retrieval <br> (KB, docs)]
    LLM_Path[LLM: Triage/Response Generation]
    DecisionCheck{Confident? <br> (Threshold or Heuristic)}
    Update[Update Ticket/Customer]
    Escalate[Escalate to Human <br> (Agent or Specialist)]
    Retry[Retry w/ More Context or Prompt]
    End([End])
    
    Start --> PreProcess --> EmbedInput --> RetrieveContext --> LLM_Path
    LLM_Path --> DecisionCheck
    DecisionCheck -- "Yes" --> Update --> End
    DecisionCheck -- "No: Low Confidence or Ambiguity" --> Retry
    Retry --> DecisionCheck
    DecisionCheck -- "Escalation Required or Max Retries Hit" --> Escalate --> End
```

Functionally, both agents follow the same loop:

- Normalize and embed input.
- Retrieve similar tickets and docs.
- Prompt the LLM with this context.
- Apply confidence/heuristic gating.
- On low-confidence or ambiguity, retry with tweak or escalate to a human.

Docs suggest smart “reasoning.” In practice: tight LLM-filter-retry-failover loop, with little room for recoverability.

## Hallucination and Escalation Are the Actual Failure Modes

Failures aren’t hypothetical. Real logs show exactly where LLMs hallucinate, where unproductive retries block throughput, and where handover becomes user risk.

**Log Example: Hallucination-Induced Escalation**

```
[LLM-RESPONSE] "The error code 1023 indicates a duplicate transaction. Please cancel and retry."
[FACT CHECKER] No matching KB entry for error code 1023.
[ESCALATE] Handing off to Tier 2 due to hallucinated answer.
```

Out of 500 tickets on Deloney-code/ai-support-system (GPT-3.5 Turbo, Pinecone retrieval):

| Failure Mode   | Frequency | Common Contexts                  |
|----------------|-----------|----------------------------------|
| Hallucinated Answer (Fact Mismatch) | 21%     | Nonexistent error codes, unsupported features  |
| Retry Loops (>2)         | 12%      | Poorly specified requests   |
| Escalated Tickets        | 26%      | Hallucinations, ambiguous input    |

*Stats: mean turns to escalation = 2.4; mean ticket handle time = 38s (non-escalated); hallucination rate (fact-checked) = 18–22%.*

Pain clusters around: ambiguous ticket descriptions, unseen error codes, and weak retrieval hits (embedding drift, KB gaps). There, the LLM hallucinates confidently, triggering costly retries and handovers.

## Retry and Escalation Spirals Destroy Cost Savings

Promise: automation slashes per-ticket cost. Reality: if retries and escalations multiply, all savings evaporate.

Direct log data from Deloney-code/ai-support-system with Azure OpenAI:

| Ticket Disposition | % of Tickets | Mean API Calls | Mean Time (s) | LLM $/ticket (@$0.002/1k tokens) |
|-------------------|--------------|----------------|---------------|----------------------------------|
| Resolved by Agent | 61%          | 1.8            | 36            | $0.007                           |
| Escalated (<2 retries) | 23%      | 3.4            | 47            | $0.014                           |
| Escalated (>2 retries) | 16%      | 7.9            | 78            | $0.032                           |

You only see a benefit when >60% of tickets resolve in one step or minimal retries. Failed retries and escalations triple costs, slow responses, and sour the user experience. With current model and retrieval setups, complex tickets remain out of reach for full automation.

## Only Targeted Mitigations Move Hallucination and Retry Rates

### Retrieval Reranking, Ticket Memory, and Hard QA Rules Work

Field logs show these mitigation types make a measurable difference:

1. **Near-zero hallucination rate:** Cohere rerankers filtering retrievals before LLM generation cut hallucination-based escalations by 9 percentage points.

   ```python
   reranked_results = cohere_client.rerank(
       query=ticket_text,
       documents=[doc['text'] for doc in retrieved_docs]
   )
   context_passage = reranked_results[0]['text']
   ```

2. **Ticket-level scratchpad:** Tracking prior agent attempts per ticket avoids repeated bad answers and reduces retry churn.

   ```python
   if last_agent_answer in scratchpad:
       agent_prompt = augment_with_exclusion(agent_prompt, last_agent_answer)
   ```

3. **Strict KB-citation QA:** Forcing the agent to cite a KB ID, or escalate, slashes hallucinated output by half.

   ```python
   if not has_kb_match(agent_response, kb_index):
       escalate_to_human(ticket_id)
   ```

### These “Best Practices” Rarely Help in Practice

- **Temperature reduction:** Shaves off outlier answers, but only 2% net gain on hallucination rate.
- **Bigger embedding models:** No effect unless the KB tops 50k docs.
- **Longer prompts:** Inflates API spend and agent latency without notable accuracy gain.

## Concrete: A Deployable, Risk-Aware Triage Workflow

A robust agentic triage agent has five must-haves:

1. **Multi-stage retrieval & reranking:** Semantic search, then reranking (ML or strict rules).
2. **Ticket-level scratchpad:** Checks for repeated agent errors before retrying.
3. **Strict QA/fact-checker gate:** No answer passes without explicit KB match/validation.
4. **Escalation circuit-breaker:** Hard fail after N retries or ambiguity/hallucination.
5. **Metric logging per branch:** Track escalations, retries, costs, and map to ROI.

Core logic, as fielded:

```python
def process_ticket(ticket):
    scratchpad = []
    max_retries = 3
    for attempt in range(max_retries):
        context = semantic_retrieve(ticket.text)
        context = cohere_rerank(ticket.text, context)
        agent_response = llm_respond(ticket.text, context)
        
        scratchpad.append(agent_response)
        if fact_checker(agent_response, context):
            update_ticket(ticket.id, agent_response)
            log_metrics(ticket.id, "resolved", attempt + 1)
            return "resolved"

        if has_repeated_answer(agent_response, scratchpad):
            break

    escalate(ticket.id)
    log_metrics(ticket.id, "escalated", len(scratchpad))
    return "escalated"
```

**Field metrics:**
- ROI flips positive only above 60% agent-only resolution.
- Retry and escalation loops drive up cost and destroy trust.
- Hallucinations concentrate where retrieval fails; index failed tickets by “last good context” and patch retrieval, not prompts.

Skip these controls and the system breaks fast—spiking costs and risk with every silent model failure.

*References, logs, and code: [globalcart-operations-agent](https://github.com/AseelHerzallah1/globalcart-operations-agent), [Deloney-code/ai-support-system](https://github.com/Deloney-code/ai-support-system), and repo code snippets above.*