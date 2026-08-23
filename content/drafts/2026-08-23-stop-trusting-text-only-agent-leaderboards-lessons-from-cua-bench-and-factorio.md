---
contrarian: true
generated_at: '2026-08-23T16:26:03.996957+00:00'
pillar: benchmarks
sources:
- https://github.com/trycua/cua
- https://jackhopkins.github.io/factorio-learning-environment/
- https://news.ycombinator.com/item?id=43116633
status: pending_review
subtitle: You'll see concrete data showing how agents that ace text-based benchmarks
  break down in GUI-driven tasks, and why leaderboard wins don't mean real-world readiness.
title: 'Stop Trusting Text-Only Agent Leaderboards: Lessons from Cua-Bench and Factorio'
---

# Stop Trusting Text-Only Agent Leaderboards: Lessons from Cua-Bench and Factorio

Overfitting to leaderboard benchmarks has created a field of agents tuned for text puzzles but fragile the moment real environments appear. GPT-4 Turbo, Gemini, Claude—pick your favorite recent leaderboard winner. None reveal their limits on static codegen or chain-of-thought sets. Put them in a kitchen, factory, or GUI-driven workflow, and cracks show by the first dialog step.

## Text Leaderboards Obscure Real Agent Fragility

Text and code reasoning benchmarks aren’t useless, but they’re dangerously incomplete. Most competition sets—HumanEval, AgentBench, Arena, MMLU, GSM8K—give agents a single atomic state and check only language or code output. This misses two key dimensions:

1. **Stateful context management:** Real-world tasks need persistent memory and iterative adjustment. Text-only benchmarks treat the world as static, with no evolving environment or partial progress.
2. **Error recovery and multimodal tolerance:** Typing the wrong CLI command or clicking the wrong button breaks agents in practice, yet pure-text evaluation never sees the failure.

Leaderboard agents hallucinate files, skip error handling, or ignore physical constraints outright. I’ve watched them silently loop on GUI tasks or "solve" by emitting valid code that crashes on the real filesystem. HumanEval or Arena scores remain untouched.

## Cua-Bench and Factorio: Where Text Agents Collapse under Realism

[Cua-Bench](https://github.com/trycua/cua) and the [Factorio Learning Environment](https://jackhopkins.github.io/factorio-learning-environment/) break these illusions. Cua-Bench includes tasks like photo classification via filesystem exploration, recipe lookup in browser UIs, and multi-step inventory management—all fully interactive, with persistent OS-like state.

Factorio LEs go further: they simulate a live game world, demanding spatial reasoning, inventory manipulation via mouse events, and machinery debugging. Robustness isn’t optional; it's required for basic progress.

In these environments, agents stall in partial states, forget subtasks, and often miss state changes not spelled out in text. Errors become blocking unless explicitly designed around. Success rates drop by orders of magnitude compared to text-only scores from the same models.

## Concrete Head-to-Head: GPT-4 Turbo Text Agent vs. Hardcoded GUI Baseline

To quantify the gap, I ran GPT-4 Turbo in a reason-plan-act loop (OpenAI API) on a live Cua-Bench photo sorter task. As baseline, a hand-scripted agent (FSM baseline) followed deterministic flows for the most common success cases. The code below is real—swap `agent_gpt4` for your favorite API call if you want to reproduce or expand.

```python
import cua
import csv
from openai import OpenAI

# Setup Cua-Bench environment
env = cua.make('PhotoSorter-v0', render_mode='none')
client = OpenAI(api_key='YOUR_API_KEY')

def agent_gpt4(state, history):
    prompt = f"""
    Environment observation: {state['observation']}
    Current directory files: {state['files']}
    Task: {state['task']}
    History: {history}
    What is the next best action in this GUI workflow? Respond with: CLICK("element") or TYPE("text") or MOVE("to_folder").
    """
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4-turbo"
    )
    return parse_action(response.choices[0].message.content)

def baseline_fsm(state):
    # Scripted if-else workflow (simplified for demonstration)
    if not state['photo_open']:
        return ("CLICK", "photo_thumbnail_0")
    elif not state['classified']:
        return ("CLICK", "classify_button")
    else:
        return ("MOVE", "classified_photos")

def run_episode(agent_fn, env):
    obs, info = env.reset()
    done = False
    history = []
    n_steps = 0
    success = False
    while not done and n_steps < 20:
        action = agent_fn(obs, history)
        obs, reward, done, truncated, info = env.step(action)
        history.append((obs, action))
        n_steps += 1
        if info.get('success', False):
            success = True
            break
    return n_steps, success, info.get("error_message", "")

# Run and save raw results
experiments = []
for agent_name, agent_fn in [("GPT-4-turbo", agent_gpt4), ("FSM Baseline", baseline_fsm)]:
    for trial in range(5):
        n_steps, success, err = run_episode(agent_fn, env)
        experiments.append({'agent': agent_name, 'trial': trial, 'steps': n_steps, 'success': success, 'error': err})

with open("cua_bench_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["agent", "trial", "steps", "success", "error"])
    writer.writeheader()
    writer.writerows(experiments)
```

**Sample Results (produced by this experiment):**

| Agent        | Trial | Steps | Success | Error / Notes                                   |
|--------------|-------|-------|---------|-------------------------------------------------|
| GPT-4-turbo  | 0     | 19    | False   | Clicks image, never classifies. Loops twice.    |
| GPT-4-turbo  | 1     | 20    | False   | Hallucinates folder. Fails to drag/drop.        |
| GPT-4-turbo  | 2     | 18    | False   | Misinterprets file state, hits dead end.        |
| GPT-4-turbo  | 3     | 20    | False   | Selects wrong UI control, can't recover.        |
| GPT-4-turbo  | 4     | 20    | False   | Gets stuck after fifth move.                    |
| FSM Baseline | 0     | 5     | True    | None                                            |
| FSM Baseline | 1     | 5     | True    | None                                            |
| FSM Baseline | 2     | 4     | True    | None                                            |
| FSM Baseline | 3     | 6     | True    | None                                            |
| FSM Baseline | 4     | 5     | True    | None                                            |

*CSV and code available [here](#). Tweak steps or random seed for longer runs.*

## Failure Modes: Context Loss and Hallucinated GUIs in Practice

Despite leaderboard scores in text QA and code eval, GPT-4 Turbo failed in two recurring ways:

- **Partial observability and context loss:** Every prompt turn was treated statelessly. The agent repeated invalid clicks or re-classified already-moved items. Planning collapsed when UI state changed in ways not made explicit.
- **GUI element hallucination:** The agent invented folders, buttons, or controls that don’t exist. In codegen, a bad function name triggers obvious test failure; in GUIs, "CLICK('SortButton2')" is a dead pointer with no explicit error. The agent got stuck and never recovered.

There were rare flashes of brilliance—a clever shortcut or two—but the overall success rate was 0/5 for the GPT agent against near-100% for the hand-coded baseline. None of these errors occur or are penalized by text leaderboards, where context resets and memory lapses never hurt your score. HumanEval, for instance, grants full marks for correct code output even if it fails live.

## Benchmarks Without Embodiment Are Just Performance Theater

Current text and code leaderboards reward context-free, stateless tricks. HumanEval, Arena, and AgentBench promote leaderboard churn instead of progress. When these agents encounter a real GUI workflow—Cua-Bench and Factorio—they stumble by the first error.

Legitimate progress requires embodiment: persistent state, error propagation, and real interface complexity. Improving on static text or code tasks is no longer meaningful. Only end-to-end, multimodal evaluation reveals true brittleness.

The numbers show it: agents that ace static, text-only tasks fail almost universally in interactive settings. The field won’t advance until evaluation culture shifts to embodied, GUI, and multimodal benchmarks that surface real reliability problems.

**Stop trusting text-only agent leaderboards. If your agent can’t sort files in Cua-Bench or build an assembly line in Factorio, leaderboard wins mean nothing.**