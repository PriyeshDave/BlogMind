## Title: I Built an AI Agent That Writes and Publishes My Blog — Here's the Real Architecture (and Every Bug I Hit)

### Subtitle: Sourcing, drafting, critique, human review, and multi-platform publishing — fully automated, running on a 2-day cadence, with the production failures nobody's blog post about "AI content automation" ever shows you.

---

Most posts about "AI content automation" show you a single prompt and a screenshot. That's not automation — that's a demo. Real automation means a pipeline that runs unattended for weeks, survives API changes, recovers from partial failures, and doesn't quietly publish garbage while you're not watching.

I built one of these for my own technical blog. It's called **BlogMind**, and this is the actual architecture — including the four production bugs that would have silently broken it if I hadn't caught them.

## The problem with "just prompt an LLM to write blog posts"

A single prompt that says "write me a blog post about AI agents" produces exactly what you'd expect: generic, structurally sound, and forgettable. It has no opinion, no verified facts, and no artifact a reader can actually use. Worse, if you automate *publishing* that output directly, you've built a machine for damaging your own credibility at scale.

The actual engineering problem isn't "generate text." It's:

- How do you make the model pick topics that are *actually worth writing about*, not just whatever's trending?
- How do you stop it from hallucinating benchmarks and stats?
- How do you keep a human in the loop without turning the whole thing back into manual work?
- How do you publish to platforms that don't all have the same (or any) API?

BlogMind's architecture is built around those four questions.

## High-level architecture

```
Topic Sourcing → Topic Scoring → Outline → Draft → Critique → Style Pass
      → Human Review (GitHub PR) → Publish (dev.to → Medium → LinkedIn)
```

Every arrow in that diagram is a deliberate checkpoint, not just a pipe. Let me walk through each stage.

### 1. Topic sourcing — pulling signal, not noise

The pipeline rotates through five content pillars (Architecture Deep-Dive, Production War Stories, Framework Teardown, Business Problem Mapping, Benchmarks) so the blog develops a recognizable identity instead of feeling random. For whichever pillar is next in rotation, it pulls raw candidates from three free, unauthenticated sources:

- **arXiv** — via the public Atom feed API, filtered by relevant search terms
- **Hacker News** — via the Algolia search API, filtered to stories with real engagement (`points>20`)
- **GitHub** — trending/recently-active repos via the search API

None of this is fancy. It's `requests` and `feedparser` hitting three free endpoints. The intelligence isn't in the sourcing — it's in what happens next.

### 2. Topic scoring — the first quality gate

All those raw candidates get handed to an LLM with one explicit job: **be ruthless.** The scoring prompt is deliberately adversarial toward generic content:

> "You are ruthless about avoiding: generic 'what is agentic AI' explainer content, rehashing a framework's own docs with no independent angle, pure news reporting with no technical takeaway. You favor candidates that let the writer show real code, a real number, or a real opinion."

It returns a single chosen angle — not a topic, an *angle* — plus the reasoning for why it beat the alternatives. This is the difference between "write about LangGraph" and "LangGraph's DAG model breaks down on conditional branches unless you write your own glue code — here's what that actually looks like in production."

### 3. The drafting pipeline — four passes, not one

This is the part everyone gets wrong when they say they've "automated content." A single-shot prompt produces a single-shot draft: plausible, forgettable, occasionally wrong. BlogMind runs four distinct passes:

**Outline** — plans section-by-section structure and explicitly names the concrete artifact (code, data, or diagram) the post will contain. If the outline can't name a real artifact, the post doesn't get written.

**Draft** — writes the full post *with a web search tool enabled*, so specific claims get verified against live search results instead of being generated from parametric memory. The system prompt is explicit: don't state a number you haven't searched and confirmed.

**Critique** — a separate LLM call, prompted as a skeptical editor, checks the draft against a quality bar: minimum word count, presence of a real code block, presence of a real number, and — critically — a checklist of AI-writing failure modes (vague unsupported claims, plausible-but-broken code, padding to hit a word count). If it fails, it goes back for revision. Up to two rounds.

**Style pass** — a final tightening pass against a voice guide that explicitly bans "AI-cadence" tells: no "let's dive in," no rhetorical-question section openers, no hedging phrases, specific subheadings instead of vague topic labels.

Here's the actual voice guide excerpt, because I think prompt engineering like this matters more than the pipeline plumbing:

```
- Take positions. Say what's overrated, what breaks, what the docs
  don't tell you. Avoid both-sides-ism unless the tradeoff is
  genuinely balanced.
- Use subheadings that are specific claims, not vague topic labels.
  E.g. "ReAct loops fail silently past 15 tool calls" beats
  "Challenges with ReAct."
- Code blocks must be realistic and runnable, not pseudocode
  dressed as code, unless explicitly illustrating pseudocode.
```

### 4. The human review gate — the part I refused to automate

This is the most important architectural decision in the whole system: **a human has to merge the pull request.**

The pipeline commits the finished draft to a new git branch and opens a GitHub Pull Request, labeled `blog-draft`, with the metadata (pillar, sources consulted, a review checklist) laid out for the reviewer. Nothing publishes until that PR is merged.

I caught this rule proving itself in the very first real draft the pipeline produced. It generated a post titled *"Why We Ditched Vectors and Graphs for SQL in Agent Memory Systems"* — first person, implying a real production migration story. The content never actually described a real system. It was a fabricated anecdote wrapped around a genuinely good technical argument. A fully autonomous pipeline would have published that as-is. The review gate caught it before a single reader saw it.

That's not a hypothetical safety feature. That's the system doing exactly what it was built to do, on the first real run.

### 5. Publishing — three platforms, three different problems

Once a PR merges, a second GitHub Actions workflow fires and publishes to three destinations, each with its own constraint:

**dev.to** — has a clean, open API. This is the pipeline's canonical source until I deploy my own Astro/Next.js site.

**Medium** — closed its public API to new integrations back in 2023. There's no supported way to publish there programmatically anymore. The workaround: dev.to publishes first, then Medium's own "Import a Story" tool pulls the article in by URL and — usefully — sets its canonical URL back to dev.to automatically, so there's no duplicate-content SEO penalty. This is the one manual step left in the whole pipeline: paste a URL, review formatting, click publish. About thirty seconds.

**LinkedIn** — has a real API (the Posts API), but getting there requires creating a Developer App tied to a Company Page, requesting the `Share on LinkedIn` and `Sign In with LinkedIn` products, and running a one-time interactive OAuth flow to get an access token (which expires every 60 days — there's no getting around babysitting this periodically).

## The bugs — because this is the part nobody shows you

Here's what four "small" bugs looked like in a real CI environment, and why each one is a lesson about automation generally, not just about this project.

**Bug 1: A file write that only broke in one code path.**
```python
with open(out_path, "wb") as f:
    frontmatter.dump(post, f)
```
`frontmatter.dump()` writes a string, not bytes. Opening the file in binary mode (`"wb"`) crashed the moment it tried to write — but `open(path, "wb")` *creates and truncates the file the instant it's called*, before the crash. So every failed run left behind a real, tracked, completely empty `.md` file, silently sitting in the repo like a tombstone. Fix: open in text mode (`"w"`). Lesson: a crash mid-write can still leave debris on disk — check for that debris, don't assume a failed run left nothing behind.

**Bug 2: A CI-only import error that never showed up locally.**
```python
python scripts/check_cadence.py
```
run this way, Python only adds `scripts/` to its import path — not the repo root. `from src.utils.settings import get_settings` worked perfectly on my machine because I'd always run the pipeline as `python -m src.generation.pipeline` (which *does* add the repo root). The cadence script, invoked differently, threw `ModuleNotFoundError` on every single CI run. Lesson: how you invoke a script changes Python's import resolution — test the exact invocation the automation actually uses, not a convenient local equivalent.

**Bug 3: A silent failure hidden behind a Unix pipe.**
```bash
DRAFT_PATH=$(python -m src.generation.pipeline | tail -n 1)
```
If the pipeline crashes partway through, `python` exits non-zero — but `tail` still exits zero (it successfully read whatever partial output it got before the crash). Bash reports the *last* command's exit code for a pipeline by default. So the step showed a green checkmark while silently having generated nothing. Fix: capture output via command substitution directly (`OUTPUT=$(python ...)`) instead of piping through a second command, so the real exit code propagates. Lesson: piping output through a formatting command can mask the exit code of the thing that actually matters.

**Bug 4: Git history assumptions that don't survive a shallow clone.**
```bash
FILE=$(git diff --name-only HEAD^ HEAD -- content/drafts/ | head -n 1)
```
This assumed there'd always be at least two commits of history to diff against. With `fetch-depth: 1` (a shallow clone — the CI default for speed), `HEAD^` doesn't exist. `git diff` failed, the file path came back empty, and every downstream publish step was silently skipped by its `if` guard. Fix: stop inferring "what changed" from git history entirely — just check what's actually sitting in the drafts directory on disk. Lesson: don't reconstruct state from git history when you can just check the filesystem directly; it's more robust and doesn't depend on merge strategy or clone depth.

Every one of these bugs is the same shape: **something failed quietly and the automation kept reporting success.** That's the actual risk profile of unattended systems — not "it crashes loudly," but "it silently stops doing its job and you don't find out until you go looking."

## The tech stack

| Layer | Tool |
|---|---|
| Drafting model | OpenAI (`gpt-4.1`) via the Responses API, with the hosted `web_search` tool |
| Topic sourcing | arXiv Atom API, Hacker News Algolia API, GitHub Search API |
| Orchestration | GitHub Actions — one workflow for generation (daily cron, self-throttled to a 2-day cadence), one for publishing (triggered on PR merge) |
| Review | GitHub Pull Requests — the human checkpoint |
| Publishing | dev.to REST API, Medium's Import Story tool (semi-manual), LinkedIn Posts API (`/rest/posts`) |
| State | A single JSON file (`content/.pipeline_state.json`), committed back to the repo by the workflow itself, tracking pillar rotation and last-run timestamp |

## What I'd tell someone building something similar

**Put the human checkpoint where it actually matters, not where it's convenient.** I automated sourcing, drafting, and publishing entirely, but kept exactly one manual gate: reading the PR before merge. That's the highest-leverage checkpoint in the whole system, and removing it would have meant publishing a fabricated anecdote to a technical audience within the first week.

**Design for partial failure, because it will happen at 3am while you're asleep.** Every bug above is a partial-failure mode: a crash that leaves debris, a step that silently no-ops, output that looks successful but isn't. None of these are exotic — they're the default failure mode of any multi-step automated pipeline, and the fix is almost always "stop trusting inferred state (git history, exit codes through pipes) and check ground truth directly (the filesystem, the actual exit code)."

**Treat platform API constraints as first-class architecture, not an afterthought.** Medium closing its API in 2023 isn't a footnote — it's a real constraint that shapes the whole publishing flow, and pretending otherwise (or trying to scrape around it) would have been worse than just accepting a 30-second manual step.

BlogMind now runs unattended, generating a reviewed, cited, code-backed technical post every two days, publishing to three platforms with one PR merge as the only manual action. It took roughly a dozen "small" bugs to get there — and every one of them is now the reason the system doesn't quietly fail without telling me.
