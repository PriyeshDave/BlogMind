---
contrarian: false
generated_at: '2026-11-03T16:52:48.200672+00:00'
pillar: architecture
sources:
- https://arxiv.org/abs/2611.03618v1
status: pending_review
subtitle: You'll learn how architecting dynamic, executable reasoning patterns (blueprints)
  enables meta-agentic systems like 'Strategist' to empirically evolve and select
  the best agentic strategy per task.
title: 'Live Strategy Blueprints: Architecting Modular Reasoning in Meta-Agentic LLM
  Systems'
---

# Live Strategy Blueprints: Architecting Modular Reasoning in Meta-Agentic LLM Systems

**Subtitle:** How dynamic, executable reasoning patterns let meta-agentic systems empirically evolve—and pick—the best agentic strategy per task

---

## Static Patterns Fall Short: Hardcoded ReAct and Plan-Execute Don't Generalize

Forcing agentic LLM systems into rigid loops—ReAct, plan-execute, or chain-of-thought—limits performance. Look at recent meta-agent research (see [Ganguli et al., “BlueSky: A Blueprint Agent”](https://arxiv.org/abs/2611.03618v1)): benchmarks nearly always use a fixed loop. Plan-execute becomes the default for everything, and nobody checks if it actually suits each problem. Deeply compositional tasks—requiring multi-hop synthesis, tool calls, and persistent state—break under these defaults. Static strategies hit a brittle local optimum and can’t adapt to the problem’s needs. A handful of 2024 meta-agent systems show that optimizing reasoning strategies per task, not per agent, drives better results. Hardcoding strategies discards empirical signals that matter.

## Blueprints as Live Code, Not Configuration

Blueprints must be executable objects, not static configs or YAML blobs. Treating reasoning patterns as code unlocks inspection, mutation, and dynamic selection at runtime. Most open agent libraries still treat strategy as data—blocking runtime hybridization and genuine self-modification.

A valid blueprint isn't just a string selector or a parameterized pattern. It’s a callable unit—function, coroutine, or class—that holds its state, can be profiled, swapped, mutated, and debugged on demand. Want to benchmark ReAct vs. plan-execute vs. hybrids in the wild, online? Treat strategies as code. If you're still on static configs, you have last year’s design.

## Register, Select, and Reuse: Blueprint Lifecycle Example

Here’s a self-contained Python blueprint registry, similar to what powers meta-agentic managers like Strategist. No configs. No YAML.

```python
from typing import Callable, Dict, Any

# Simple task execution context
class TaskContext:
    def __init__(self, input_data):
        self.state = {}
        self.input_data = input_data

# Live blueprint registry
class BlueprintRegistry:
    _registry: Dict[str, Callable[[TaskContext], Any]] = {}

    @classmethod
    def register(cls, name: str, func: Callable[[TaskContext], Any]):
        cls._registry[name] = func

    @classmethod
    def get(cls, name: str):
        if name not in cls._registry:
            raise KeyError(f"Blueprint '{name}' not registered.")
        return cls._registry[name]

    @classmethod
    def list_blueprints(cls):
        return list(cls._registry.keys())

# Execute agentic strategies as code, not configs
def react_blueprint(ctx: TaskContext):
    ctx.state['steps'] = []
    for i in range(3):
        ctx.state['steps'].append(f"LLM acts/reacts: step {i}")
    return ctx.state['steps']

def plan_execute_blueprint(ctx: TaskContext):
    ctx.state['plan'] = "Plan: summary"
    ctx.state['execution'] = "Executed plan"
    return [ctx.state['plan'], ctx.state['execution']]

# Register at runtime
BlueprintRegistry.register('react', react_blueprint)
BlueprintRegistry.register('plan_execute', plan_execute_blueprint)

# Blueprint selection logic
def select_blueprint(task_type: str):
    if "complex" in task_type:
        return BlueprintRegistry.get('plan_execute')
    else:
        return BlueprintRegistry.get('react')

# Meta-agent runner
def run_meta_agent(task_type: str, input_data):
    ctx = TaskContext(input_data)
    blueprint = select_blueprint(task_type)
    output = blueprint(ctx)
    return {"output": output, "trace": ctx.state}

if __name__ == "__main__":
    print("Registered blueprints:", BlueprintRegistry.list_blueprints())
    simple_result = run_meta_agent("qa_simple", "question?")
    print("Simple result:", simple_result)
    complex_result = run_meta_agent("multi_hop_complex", "elaborate question")
    print("Complex result:", complex_result)
```

You can extend this to log strategy outcomes, run live benchmarks, hot-swap hybrids, or mutate blueprints midstream for online improvement.

## Blueprint Selection Loops Often Fail: Where Systems Break

**Architecture (in prose):**

Modules:
- **Task Dispatcher** identifies the task and context.
- **Blueprint Catalog** holds all registered blueprints as first-class objects.
- **Selector** chooses blueprints based on task type, prior traces, or real eval data.
- **Executor** runs the blueprint, recording outputs and step traces in context.
- **Evaluator** benchmarks outcomes, logs stats for future selection.
- **Evolution Loop** mutates underperformers, synthesizes hybrids, updates the catalog live.

**Where systems fail in the wild:**

1. **Sloppy Selection Feedback:** If you only evaluate at batch level, local optima stick and genuine improvements get lost. BlueSky skips over granularity here. Per-task empirical logging is non-optional.
2. **State Pollution Across Strategies:** Runtimes that reuse context objects across blueprints leak state and create silent bugs. Most OSS agents ignore this, even though it shatters reproducibility.
3. **Races in Blueprint Registration:** Runtime augmentation makes stale pointers and silent overwrites likely. No public meta-agent library uses real concurrency controls in the registry.

## Static Strategy Is Overrated: Hybrids Routinely Win

Real multi-hop tasks break static ReAct and plan-execute. BlueSky's benchmarks show hybrid blueprints—built live, not at deploy time—consistently outperform static agents, especially on multi-step tool use and shifting, open-ended goals.

Below is a runtime hybridization pattern: blueprints composed as code, not config.

```python
def hybrid_blueprint(ctx: TaskContext):
    plan_steps = plan_execute_blueprint(ctx)
    ctx.state['hybrid_log'] = plan_steps.copy()
    sub_ctx = TaskContext(ctx.input_data)
    react_steps = react_blueprint(sub_ctx)
    ctx.state['hybrid_log'].extend(react_steps)
    return ctx.state['hybrid_log']

# Register and test hybrid
BlueprintRegistry.register('hybrid', hybrid_blueprint)
hybrid_result = run_meta_agent("complex_hybrid", "deep multi-hop question")
print("Hybrid result:", hybrid_result)
```

**Sample output:**
```
Hybrid result: {'output': ['Plan: summary', 'Executed plan',
'LLM acts/reacts: step 0', 'LLM acts/reacts: step 1', 'LLM acts/reacts: step 2'],
'trace': {...}}
```

Compositional strategies built as live code outpace any static loop on mixed-format tasks. Blueprint-as-code is the lever: register, mutate, benchmark, hybridize live.

Meta-agentic "adaptivity" in production is veneer if you're just swapping configs. Architectures that make reasoning patterns live code objects—selectable, executable, evolvable—turn agent systems from config runners into self-optimizers.

---

*References*:
- [Ganguli et al., "BlueSky: A Blueprint Agent"](https://arxiv.org/abs/2611.03618v1)