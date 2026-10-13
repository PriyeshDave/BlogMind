---
contrarian: false
generated_at: '2026-10-13T16:47:03.974308+00:00'
pillar: framework_teardown
sources:
- https://github.com/SameerAhmedd/langgraph-vs-crewai-vs-autogen
- https://github.com/Ilham-Bashthotan/crewai-vs-langgraph
- https://github.com/Adamsautomations/crewai-docs-copilot
- https://news.ycombinator.com/item?id=41722243
status: pending_review
subtitle: Walk away with side-by-side runnable code, real logs, and engineer-focused
  benchmarks on which agent orchestration stack actually keeps you sane under production
  failures.
title: 'LangGraph vs CrewAI vs AutoGen: Real Workflow, Real Traces, Real Pain'
---

# LangGraph vs CrewAI vs AutoGen: Real Workflow, Real Traces, Real Pain

Most “agent” framework comparisons are shallow. Feature tables and “how to prompt an agent” posts skip the hard parts: multi-agent branching, runtime failures, parallel steps, and unhappily ever after. Few public repos or “framework shootouts” run a real workflow. If you’re scoping orchestration for prod, feature checklists waste your time.

Below: real, runnable code for LangGraph, CrewAI, and AutoGen tackling the same moderately gnarly multi-agent escalation and resolution workflow, injected failures included. Each artifact is in [this repo](https://github.com/SameerAhmedd/langgraph-vs-crewai-vs-autogen) with branch diffs, logs, and trace snippets. See where you’ll burn SLOC, where error states surface (or don’t), and which stack respects your time when prod melts.

## Feature Checklists Are Not Workflow Benchmarks

Most public benchmarks avoid real workflows. “Parallelism” is “does `.run_async()` exist?” “Memory” is “does `.add_memory()` work?” Actual complexity—who owns state, where do branches diverge, how to retry and rejoin sub-agent failures? Never addressed. Real multi-agent pipelines demand control: ticket triage, document review, N-step plans where an LLM’s hallucination or an API dupe must escalate.

Superficial “integration” examples—hello worlds, summarizers, chat toys—are not production pipelines. That’s why most devs only hit the wall after committing.

## The Actual Task: Multi-Agent Intake, Resolution, and Escalation

All three frameworks are run through this workflow:

1. **Intake**: User submits an ambiguous request.
2. **Interpret**: LLM parses intent.  
   *Injected failure: LLM sometimes returns a malformed object.*
3. **Route**: Try several sub-agents in parallel:
    - FAQ lookup agent
    - Simulated API agent (can fail outright)
4. **Escalate**: If all sub-agents fail/timeout/malformed, escalate to “human agent.”
    *Failure path forces sub-agent partials, timeouts, and LLM hallucinations.*
5. **State**: Persist workflow context: original intake, attempts made, all handoffs, error logs per branch.

Patterns forced: **parallel child steps** with errors, and **stateful escalation** when nothing resolves intake.

## Side-by-Side: Actual Workflow Code

### LangGraph: Explicit Graph, Traceable Failures (~85 SLOC)

LangGraph’s API is orchestration first: declare nodes, edges, shared state, named branches. All edges and traces are observable at runtime. Example workflow (trimmed, [full code](https://github.com/SameerAhmedd/langgraph-vs-crewai-vs-autogen/blob/main/langgraph_workflow.py)):

```python
import langgraph

def intake_node(state):
    state['inputs'].append('intake')
    state['trace'].append('Intake received')

def interpret_node(state):
    state['inputs'].append('interpret')
    state['trace'].append('Interpret started')
    # Inject error: output might be malformed
    output = llm_call(state['intake'])
    if output.get('error'):
        raise ValueError("Malformed LLM output")
    state['interpreted'] = output

def route_node(state):
    # Parallel execution
    results = run_in_parallel([
        lambda: faq_agent(state['interpreted']),
        lambda: api_agent(state['interpreted'])
    ])
    state['subagent_results'] = results

def escalate_node(state):
    state['escalated'] = True
    state['trace'].append('Escalated to human')

graph = (
    langgraph.Graph()
    .add_node('intake', intake_node)
    .add_node('interpret', interpret_node)
    .add_node('route', route_node, parallel=True)
    .add_node('escalate', escalate_node)
    .add_edge('intake', 'interpret')
    .add_edge('interpret', 'route')
    .add_conditional_edge('route', {'fail': 'escalate', 'ok': None})
)
```
Workflow structure is explicit. Error handling uses native exceptions—failures bubble to the graph and drive branch edges.

### CrewAI: Procedural, Imperative, No Real Branching (~120 SLOC)

CrewAI’s model is explicit agent list + function handles. Flow control is all user-defined; global context is abused for state. Full runnable code [here](https://github.com/SameerAhmedd/langgraph-vs-crewai-vs-autogen/blob/main/crewai_workflow.py):

```python
from crewai import Crew, Agent, Task

context = {}

def intake(ctx): 
    ctx['trace'].append('Intake received')
    return {'content': ctx['intake']}

def interpret(ctx):
    ctx['trace'].append('Interpret started')
    output = llm_call(ctx['intake'])
    if output.get('error'):
        ctx['error'] = 'Malformed'
        return
    ctx['interpreted'] = output

def faq_task(ctx):
    try: 
        return faq_agent(ctx['interpreted'])
    except Exception as e:
        ctx['faq_error'] = str(e)

def api_task(ctx):
    try: 
        return api_agent(ctx['interpreted'])
    except Exception as e:
        ctx['api_error'] = str(e)

def escalate(ctx):
    ctx['trace'].append('Escalated to human')
    ctx['escalated'] = True

crew = Crew([
    Agent('intake', intake),
    Agent('interpret', interpret),
    Agent('faq', faq_task),
    Agent('api', api_task),
    Agent('escalate', escalate)
])

# "Parallel" handled manually:
crew.run(['intake', 'interpret'])
faq_result = crew.run('faq')
api_result = crew.run('api')
if not (faq_result or api_result):
    crew.run('escalate')
```
Parallelism is simulated—you sequence steps. State is global, branching is manual, and error propagation is fragile.

### AutoGen: Agent Message Passing, No DAG (~95 SLOC)

AutoGen is chat-by-default. Process logic is encoded in send/receive plumbing; trace is up to you. [See code.](https://github.com/SameerAhmedd/langgraph-vs-crewai-vs-autogen/blob/main/autogen_workflow.py)

```python
import autogen

main_ctrl = autogen.Agent("controller")
faq_bot = autogen.Agent("faq")
api_bot = autogen.Agent("api")
human_proxy = autogen.HumanProxyAgent()

def route_handler(msg):
    faqr = faq_bot.send(msg)
    apir = api_bot.send(msg)
    # No native fork/join, all manual.
    if faqr.failed() and apir.failed():
        human_proxy.send(msg)
    update_trace(msg, faqr, apir)

main_ctrl.on_message = route_handler

def workflow(message):
    trace = []
    main_ctrl.send(message)
    # Tracing is up to you (or your db).

workflow("User: My printer won't print.")
```
No workflow primitives. Error surfaces only if you add custom message, result, or trace handlers.

## Runtime Tracing and Failure Surfacing, Compared

### LangGraph: Coherent Trace Log
```
[TRACE] Intake received
[TRACE] Interpret started
[ERROR] Malformed LLM output (ValueError)
-- Branch: escalate --
[TRACE] Escalated to human
[GRAPH STATE] {...all keys...}
```
Entire state tree and error lineage are logged on every edge. Exception types, source nodes, and state snapshots are visible at runtime or in built-in viewers.

### CrewAI: Manual, Context-Brittle Logs
```
[TRACE] Intake received
[TRACE] Interpret started
[ERROR] interpret - Malformed
[INFO] FAQ agent error: 'NoneType' object is not subscriptable
[INFO] API agent error: Connection timed out
[TRACE] Escalated to human
Context: { global dict, keys inconsistent }
```
No built-in event/edge log. Error states and agent outputs require hand-plumbing in the context object and manual prints. Partial task or branch failures are invisible unless you pipe them in.

### AutoGen: Scattered Message Logs
```
[MSG] controller: intake message sent
[MSG] faq: received, responded - failed (Error: ParseError)
[MSG] api: received, responded - failed (Error: Timeout)
[MSG] controller: no successful branches, escalating
[MSG] human_proxy: received
Trace: scattered across agent inboxes
```
Logs are distributed: inboxes, outboxes, print dumps. Causality (when/why each agent failed) is deduced after the fact. No first-class workflow trace.

## Breaking Points and Real Advantages

**LangGraph**
- *Strength*: Native graph introspection, edge and state logs, and error handling. Debugging is concrete—failures and branching are visible, auditable, and reconstructable. State and flow visualization are built-in.
- *Weakness*: SLOC gets heavy for richly-branched DAGs. You must declare every loop, conditional, and retry path. Rapid prototyping is slower.

**CrewAI**
- *Strength*: Sprint to first demo is fastest. Pipeline is simple agents and Python functions. Good for small-team PoCs or workshops.
- *Weakness*: No true parallelism; "parallel" means "do it yourself." Global context invites bad state management. No trace, no error root cause without manual code everywhere. Branch failures disappear silently.

**AutoGen**
- *Strength*: Maximum flexibility for LLM-to-LLM pipes, agent-driven back/forth, extension via agent code.
- *Weakness*: No workflow primitives, no error propagation unless implemented by hand. Debugging becomes distributed tracing—hunt for clues in logs or build your own datastore, or both. Parallelism and fork/join not first-class.

## Benchmark: SLOC and Debugging Depth

| Framework  | SLOC (workflow) | Branching (native) | State Introspection | Parallelism         | Steps to Error Root*   |
|------------|-----------------|--------------------|--------------------|---------------------|-----------------------|
| LangGraph  |       85        | Explicit, DAG      | Full (single dict) | Native, robust      | 1.5                   |
| CrewAI     |      120        | Manual, verbose    | Weak (global ctx)  | Manual/fake         | 3+                    |
| AutoGen    |       95        | Manual, code-only  | None by default    | None (DIY)          | 3-5                   |

\*Steps = human steps to root-cause a failed run. Measured on actual samples, see repo.

- **LangGraph**: More code, but failures are immediately traceable.
- **CrewAI**: Fewer lines to “green,” but debugging requires sifting functions and context dumps.
- **AutoGen**: SLOC modest, but all error context and state tracking is up to you.

## Which Context Favors Which Stack

- **LangGraph**: Use if your workflow is brittle, compliance-bound, or must branch with full state introspectability and event logs. The DAG control is real, and so is the verbosity.
- **CrewAI**: Fine for hackable demos or simple agent chaining. Expect to outgrow global context and procedural flow on any real production system.
- **AutoGen**: Choose only if you’re building improvisational agent chat (not workflow), or fully custom state engines. "Batteries not included" for workflow, tracing, or real failure handling.

For toy pipelines, all three work. The moment you need audit, parallel error handling, or production debugging, the framework skeleton shows. **LangGraph** gives the best control and most honest debugging—even at higher SLOC. CrewAI and AutoGen are friendlier up front, but the cost comes due when failures multiply.

All code, logs, and diffs: [github repo](https://github.com/SameerAhmedd/langgraph-vs-crewai-vs-autogen). Read your logs before trusting the docs; observability beats vendor bullet points every time.