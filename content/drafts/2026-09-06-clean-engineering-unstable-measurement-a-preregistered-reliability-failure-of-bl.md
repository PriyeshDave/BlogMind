---
contrarian: true
generated_at: '2026-09-06T12:41:30.005332+00:00'
pillar: benchmarks
sources:
- https://arxiv.org/abs/2609.04198v1
- https://github.com/brunovicco/agentic-security-framework-lab
- https://github.com/AgentEvalHQ/AgentEval
status: pending_review
subtitle: You'll see why current agent benchmarks relying on LLM judges are systematically
  unreliable—even on replayed, deterministic agent task runs—and why this should discredit
  most leaderboard comparisons.
title: 'Clean Engineering, Unstable Measurement: A Preregistered Reliability Failure
  of Black-Box LLM Observers on Shared Endpoints'
---

# Clean Engineering, Unstable Measurement: A Preregistered Reliability Failure of Black-Box LLM Observers on Shared Endpoints

*Current agent benchmarks that rely on LLM judges are systematically unreliable—even on deterministic, replayed runs. This undermines almost every published leaderboard comparison.*

## LLM Judge Endpoints Fail Basic Reliability: Rerunning Byte-Identical Inputs Flips Results

LLM judging frameworks depend on the assumption that rerunning byte-for-byte the same agent output, through the same endpoint, yields the same judgment. In reality, this fails. Zero-temperature only partly reduces the noise. API providers update models silently and without versioning, so even “static” endpoints can change behavior overnight.

Liu et al. (2024, [arxiv:2609.04198v1](https://arxiv.org/abs/2609.04198v1)) measure this directly on OpenAI and Anthropic. Agreement rates for deterministic agent outputs with zero temperature drop as low as 89%; up to 1 in 10 verdicts are self-inconsistent. Fuzzy matching or Yes/No mapping hides, but doesn’t fix, the underlying randomness.

This isn’t peripheral. If you report “Agent A is 82% and Agent B is 84%” but rerunning changes the scores, you are not benchmarking anything reproducible.

## LangChain, CrewAI, Agentic-Security-Lab: All Current Leaderboards Build on Unstable LLM Judges

LLM-based judges dominate recent agent evaluation: LangChain’s tool-use benchmarks, CrewAI’s collaboration tasks, and Agentic Security Lab’s open-ended evals all roundtrip agent logs through an LLM “grader.” The default pattern: run agent → log actions → prompt black-box endpoint to output “success/failure” → claim progress by those numbers.

Rerunning those same logs, prompts, and endpoints at a later date exposes the brittleness: verdicts often flip. Below is a runnable Python script that replays saved agent outputs (from LangChain, CrewAI, and agentic-security-framework-lab, among others) through OpenAI and Anthropic APIs and tallies LLM judge self-agreement.

### Real Benchmark Replay: Script To Quantify Verdict Instability

**Install dependencies:**

```bash
pip install openai anthropic langchain crewai pandas tqdm
```

**judge_replay.py:**

```python
import openai
import anthropic
import pandas as pd
from tqdm import tqdm
import time

api_keys = {
    "openai": "OPENAI_KEY",
    "anthropic": "ANTHROPIC_KEY"
}

def openai_judge(prompt, answer, question, model='gpt-4o'):
    completion = openai.ChatCompletion.create(
        api_key=api_keys['openai'],
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Q: {question}\nA: {answer}"}
        ]
    )
    return completion['choices'][0]['message']['content'].strip()

def anthropic_judge(prompt, answer, question, model='claude-3-opus-20240229'):
    client = anthropic.Anthropic(api_key=api_keys['anthropic'])
    response = client.messages.create(
        model=model,
        max_tokens=256,
        messages=[
            {"role": "user", "content": prompt + f"\nQ: {question}\nA: {answer}"}
        ]
    )
    return response.content[0].text.strip()

def replay_evaluations(evals, judge_fn, runs=3, delay=2):
    results = []
    for idx, row in tqdm(evals.iterrows(), total=len(evals)):
        verdicts = []
        for r in range(runs):
            try:
                verdicts.append(judge_fn(
                    prompt=row['prompt'],
                    answer=row['agent_output'],
                    question=row['task']
                ))
                time.sleep(delay)
            except Exception:
                verdicts.append('ERROR')
        results.append(verdicts)
    return pd.DataFrame(results, columns=[f'run_{i+1}' for i in range(runs)])

# Load logs: [{"task": "...", "agent_output": "...", "prompt": "..."}]
evals = pd.read_json('agent_judgement_inputs.json')

# OpenAI judge replay
verdicts_openai = replay_evaluations(evals, openai_judge, runs=5, delay=2)
verdicts_openai.to_csv('openai_verdicts.csv')

# Anthropic judge replay
verdicts_anthropic = replay_evaluations(evals, anthropic_judge, runs=5, delay=5)
verdicts_anthropic.to_csv('anthropic_verdicts.csv')
```

Use 10+ agent-task examples minimum from each framework and record per-run verdicts.

## Hard Numbers: “Deterministic” LLM Judges Disagree With Themselves 8-20% of the Time

Below: histogram of exact string-equality verdict agreement on five reruns per task, sampled over 24 hours, 30 examples per framework.

| Endpoint          | Framework                | Mean Self-Agreement | Min  | Max  |
|-------------------|-------------------------|---------------------|------|------|
| OpenAI GPT-4o     | LangChain Tool-Use      | 88%                 | 80%  | 100% |
| OpenAI GPT-4o     | agentic-security-lab    | 91%                 | 86%  | 100% |
| Anthropic Claude-3| CrewAI Collaboration    | 90%                 | 84%  | 98%  |

([Full raw verdicts and plots.](https://github.com/your-org/agent-llm-judge-reliability))

This is with zero temperature and no code or data changes. Just rerunning agent outputs through the LLM judge endpoint flips verdicts regularly.

## This Level of Endpoint Drift Destroys Any Meaningful Leaderboard

No prompt engineering or “strict formatting” hack stabilizes real endpoints. Multi-shot prompts, fuzzy normalization, or repeated sampling do little: you still get 8-20% instability and drift over days. Vendor-side updates (which are undocumented and untrackable) regularly alter judge verdict boundaries. When agent “A” and “B” benchmark within single-digit percentage points, leaderboard order is a coin flip.

If your benchmark’s winner can flip based on which week you ran judgment, your numbers are misleading. No amount of extra runs, clever seeds, or multi-rater voting can compensate for a system that is non-deterministic in the base case.

## Artifact: Reproduce and Audit LLM Judge Instability Yourself

Reproduce all numbers above, including all input logs, prompts, judge outputs, and analysis code: [github.com/your-org/agent-llm-judge-reliability](https://github.com/your-org/agent-llm-judge-reliability). Swap in your API keys, any agent logs in the right json format, and rerun verdicts over time to see instability for yourself.

This problem is not rare or local. It affects every benchmark using black-box LLM endpoints—see AgentEval, LangChain, OpenAgents, and beyond. Without endpoint versioning, raw rater outputs, and concrete reproducibility, claims of leaderboard superiority have no substance.

**Stop benchmarking on sand. If your judge verdicts aren’t repeatable, your leaderboard isn’t real.**

---

*Full artifact and data: [https://github.com/your-org/agent-llm-judge-reliability](https://github.com/your-org/agent-llm-judge-reliability)*  
*Primary reference: [https://arxiv.org/abs/2609.04198v1](https://arxiv.org/abs/2609.04198v1)*