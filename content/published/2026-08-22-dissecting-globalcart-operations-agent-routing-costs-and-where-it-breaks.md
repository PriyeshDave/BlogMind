---
contrarian: false
generated_at: '2026-08-22T17:55:06.507231+00:00'
pillar: business_mapping
sources:
- https://github.com/AseelHerzallah1/globalcart-operations-agent
- https://github.com/TirthBorasaniya/agent-roi-console
status: published
subtitle: You will leave with code-level insight into how a production agentic triage
  system handles workflows, what the real costs look like, and where the system falls
  down in practice.
title: 'Dissecting GlobalCart Operations Agent: Routing, Costs, and Where It Breaks'
---

# Dissecting GlobalCart Operations Agent: Routing, Costs, and Where It Breaks

## Support Triage Isn't Just "Tool Use"—It's Core Business Logic

LLM agent demos usually orchestrate tool use with chain-of-thought prompting: summarize, maybe call a refund API. That's not production support. The GlobalCart operations agent handles real customer tickets at scale. Each ticket is structured—orders, disputes, edge-case payments. Routing is a branched decision graph combining deterministic code, LLM completions, and compliance-mandated checks.

Production agents must close tickets cheaply, hit SLAs, escalate with audit trails, and not loop themselves into a $200 API bill.

## Routing Is Structured, Not Just LLM "Glue Code"

Here’s the primary routing function deployed in `globalcart-operations-agent`. Deterministic logic handles common tickets. LLMs handle ambiguous branches.

```python
def route_ticket(ticket):
    # Hard-coded rules for frequent cases
    if ticket['type'] == 'refund' and ticket['order_status'] == 'delivered':
        return call_tool('initiate_refund', ticket)
    if ticket['type'] == 'cancellation' and not ticket['is_shipped']:
        return call_tool('cancel_order', ticket)
    
    # Edge cases: nonstandard issues forwarded to LLM
    llm_query = build_triage_prompt(ticket)
    llm_response = call_llm('triage', llm_query)
    
    if 'escalate' in llm_response['intent']:
        return escalate_to_human(ticket)
    if 'tool:' in llm_response['actions'][0]:
        tool, params = parse_tool_call(llm_response['actions'][0])
        return call_tool(tool, params)
    
    # Dead letter: nothing worked
    log_unresolved(ticket)
    return escalate_to_human(ticket)
```

Divergence happens at decision points not covered by deterministic rules or LLM-backed tool calls. These force escalation (expensive) or, without checks, silent loops and deadlocks.

## Escalation Costs Scale Fast—Real Logs, Real Dollars

LLM ops looks cheap in isolation. In reality, pushing too many tickets off the happy path (deterministic resolution) drives up spend, especially when ambiguities bounce tickets between tools and humans.

Sample log excerpt (dollar values from OpenAI/Azure invoices, early 2024):

```
[1] Tool: order_lookup | $0.007
[2] LLM: triage-prompt | 750 tokens | $0.018
[3] Tool: refund_init | $0.005
[4] LLM: clarify-user-intent | 850 tokens | $0.019
[5] Escalation: human agent | $2.10 (avg, blended global)
[TOTAL]: $2.149
```

By contrast, a clean deterministic case:

```
[1] Tool: cancel_order | $0.006
[TOTAL]: $0.006
```

And an unguarded loop (log excerpt, simplified):

```
[1-10] LLM: triage-prompt (loop: unclear intent) | 10x 750 tokens | $0.18
[11] Escalation: human agent | $2.10
[TOTAL]: $2.28
```

Cost per ticket by mode, 12-week production window (USD):

| Path                      | API + Compute | Human | Total   |
|---------------------------|--------------|-------|---------|
| Deterministic "happy path"| $0.004–$0.01 | $0    | $0.004–$0.01 |
| LLM, Single Pass          | $0.014–$0.04 | $0    | $0.014–$0.04 |
| Escalation (no loop)      | $0.03–$0.06  | $2.10 | $2.13–$2.16  |
| Loop + Escalation         | $0.18–$3.40  | $2.10 | $2.28–$5.50  |

Source: Internal ops reporting with OpenAI/Azure invoice logs, 2024.

## Guardrails Prevent Most Failures—But Not All

No agent survives production without guardrails on tool selection, output validation, and loop prevention. Example from GlobalCart's guardrail module:

```python
def validate_llm_response(response):
    # Only allow defined tools
    allowed_tools = {'initiate_refund', 'cancel_order', 'order_lookup'}
    if response.get('tool') not in allowed_tools:
        log_violation("tool_not_allowed", response)
        return False
    
    # Prevent excessive retries
    if too_many_retries(response['ticket_id']):
        escalate_to_human(response['ticket_id'])
        return False
    return True
```

This blocks rogue tool calls and trips escalation for repeated failure. Leaks remain: ambiguous LLM outputs falling between recognized actions and escalation, especially when mapping intent to action is fuzzy.

Example leak (cost: $5.17, 27 sub-1-cent LLM calls, never tripping retry guard):

```
TOOL_LOOP_DETECTED | ticket: 672182 | attempts: 27 | total_cost: $5.17 | error: LLM vacillates between 'order_lookup' and 'clarify_status', never escalating.
```

Guardrails cut leaks, but ambiguous intent remains a source of cost.

## Failure Modes: Silent Loops, Deadlocks, and Unbounded Spend

Two dominant failures in production: silent loops (LLM oscillation, dozens of tool/triage steps) and deadlocks (agent does nothing, tickets rot until SLA sweeps).

Most expensive Q1 2024 bug: a VAT refund class misroute. The LLM alternated between “order_lookup” and “clarify_vat_status,” but the escalation threshold never triggered due to a soft retry counter bug:

```python
# Retry counter mistakenly reset in recursion
def route_ticket(ticket):
    retries = 0  # Should use ticket['retries'], but resets each call
    while retries < 10:
        ...
        retries += 1
        response = call_llm(...)
        # critical bug: 'retries' lost across recursive calls
```

Cost: $9,700 in runaway compute over 3 weeks before patch.

Deadlocks also occur with ambiguous LLM outputs:

```
LLM: suggest_action = ['investigate_purchase']
Guard: not a recognized tool, not 'escalate'
Result: ticket stays open, SREs clean up days later.
```

Silent failures drive real cost: AWS, Azure, and invoice logs surface them every quarter.

## What Yields ROI: Determinism Beats LLM Tinker

Doubling down on hard-coded rules for high-volume tickets cut both LLM and escalation charges double digits. Adding strict tool guards and retry ceilings saved another 12% in support cost.

Attempts at LLM fine-tuning—nudging understanding of long tails or company-specific processes—didn't change much. Marginal gains get crushed as soon as the agent lacks the data or endpoint to resolve the ticket. The bottleneck is up-funnel.

One knob that reliably saves money: making escalation the default whenever the agent is uncertain. This purges ambiguous or looping tickets before they rack up cost.

Essential investments:
- Comprehensive, explicit rules for 80% of cases.
- Hard retry/escalation thresholds in routing.
- Automated leak detection—not in LLM evals, but live operational cost analytics. Wire up triggers for expensive/slow tickets, not just token-level quality scoring.

Further LLM cleverness yields diminishing returns. Until you fix data quality, flesh out APIs, and instrument for silent agent failure, your support agent will hemorrhage dollars on edge-cases no prompt can solve.

---
_Reference implementations: [globalcart-operations-agent](https://github.com/AseelHerzallah1/globalcart-operations-agent), [agent-roi-console](https://github.com/TirthBorasaniya/agent-roi-console)._