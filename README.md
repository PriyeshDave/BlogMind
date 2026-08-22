# 🧠 BlogMind

### AI-Powered Technical Content Generation & Multi-Platform Publishing

**BlogMind** is an AI-powered content engineering pipeline that automates the journey from **topic discovery to published technical content**.

Instead of relying on a single LLM prompt to generate and publish an article, BlogMind uses a **multi-stage pipeline** with dedicated stages for topic discovery, topic scoring, outlining, drafting, critique, style refinement, human review, and publishing.

The goal isn't simply to generate more content.

The goal is to build a system that can generate **useful, evidence-backed, technically credible content while keeping human judgment exactly where it matters.**

---

## ✨ What Makes BlogMind Different?

Most AI content workflows look like:

```text
Topic → LLM → Blog → Publish
```

BlogMind treats content generation as an engineering workflow:

```text
Topic Discovery
       ↓
Topic Scoring
       ↓
Outline
       ↓
Draft
       ↓
Critique
       ↓
Style / Voice
       ↓
Human Review
       ↓
Publish
```

Every stage has a specific responsibility and acts as a quality checkpoint.

The LLM is not the entire system.

**The LLM generates.  
The pipeline validates.  
The human decides.  
The platform publishes.**

---

# 🏗️ Architecture

The complete BlogMind architecture is designed around four major layers:

1. **Signal & Topic Discovery**
2. **AI Content Generation**
3. **Human Governance**
4. **Publishing & Distribution**

### High-Level Architecture

![BlogMind Architecture](docs/images/BlogMind_Architecture_Diagram.png)

> The architecture intentionally separates generation from publishing and introduces a human approval gate before content reaches external platforms.

---

# 🔄 End-to-End Workflow

```text
┌──────────────────────┐
│   Topic Discovery    │
│ arXiv • HN • GitHub  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│    Topic Scoring     │
│  Select best angle   │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│       Outline        │
│ Structure + artifact │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│        Draft         │
│ LLM + Web Research   │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│      Critique        │
│   Quality Gate       │
└──────────┬───────────┘
           ↓
      ┌────┴────┐
      │         │
    FAIL       PASS
      │         │
      ↓         ↓
   Revision   Style
      │         │
      └────┬────┘
           ↓
┌──────────────────────┐
│   Human Review       │
│    GitHub PR         │
└──────────┬───────────┘
           ↓
       PR Merge
           ↓
┌──────────────────────┐
│      Publish         │
└──────┬─────┬─────────┘
       ↓     ↓
    dev.to Medium
             ↓
         LinkedIn
```

---

# 🎯 Core Design Principles

## 1. Generate Less, But Better

The objective isn't maximum content volume.

The system actively avoids:

- generic AI explainers
- documentation rewrites
- shallow trend reporting
- unsupported technical claims
- filler content

The topic-selection stage favors ideas that allow the final article to contain **real code, real numbers, concrete experiments, implementation details, or strong technical opinions**.

---

## 2. Don't Pick Just a Topic — Pick an Angle

There is a major difference between:

> "Write about LangGraph."

and:

> "Where LangGraph's graph model becomes awkward for conditional execution—and the glue code you end up writing."

The first is a topic.

The second is an angle.

BlogMind's topic-scoring stage is designed to identify the latter.

---

## 3. Multi-Pass Generation

BlogMind does not ask one LLM call to perform the entire writing process.

Instead, the content passes through specialized stages:

```text
Outline
   ↓
Draft
   ↓
Critique
   ↓
Revision
   ↓
Style / Voice
```

This creates separation of concerns between:

- planning
- generation
- evaluation
- revision
- editorial refinement

---

## 4. Evidence Before Claims

Technical writing frequently contains information that changes quickly.

Examples include:

- API capabilities
- benchmark numbers
- library behavior
- product features
- release information
- platform limitations

The drafting stage uses web search to verify claims rather than relying exclusively on model memory.

The principle is:

> **The model can propose a claim. Evidence validates it.**

---

## 5. Human-in-the-Loop by Design

BlogMind intentionally stops before publication.

The generated article is committed to a Git branch and submitted as a Pull Request.

The human reviewer decides whether the content is ready.

```text
AI Generation
      ↓
Git Branch
      ↓
Pull Request
      ↓
Human Review
      ↓
Merge
      ↓
Publish
```

This prevents the system from automatically publishing content that may be technically plausible but personally inaccurate.

---

# 🔎 Topic Discovery

BlogMind currently sources candidate topics from multiple technical ecosystems.

### arXiv

Used to discover:

- research papers
- emerging techniques
- new AI approaches
- technical trends

The public Atom feed is used for discovery.

### Hacker News

Used to identify:

- engineering discussions
- emerging technologies
- highly engaged technical stories

Candidate stories can be filtered based on engagement signals.

### GitHub

Used to identify:

- active repositories
- emerging frameworks
- developer tools
- implementation projects

These sources provide raw signals.

The intelligence happens in the scoring stage.

---

# 🎯 Topic Scoring

Candidate topics are passed through an LLM-based scoring stage.

The scoring logic is intentionally skeptical.

It avoids topics that are:

- generic
- overly broad
- simple documentation rewrites
- purely news-oriented
- lacking a technical takeaway

It favors topics where the eventual article can demonstrate:

- real code
- real numbers
- concrete implementation details
- experiments
- technical trade-offs
- independent opinions

The result is a selected topic **angle**, along with reasoning for why it was chosen.

---

# 📝 Content Generation Pipeline

## 1. Outline

The outline stage determines:

- article title
- subtitle
- section structure
- key points
- technical depth
- required artifact

A key requirement is that the article should contain a concrete artifact.

Examples:

- code
- architecture diagram
- benchmark
- experiment
- dataset
- implementation example

If the outline cannot identify a useful artifact, the topic may not be suitable for generation.

---

## 2. Draft

The draft stage generates the complete article using:

**OpenAI GPT-4.1 via the Responses API**

The model can use hosted web search to research current information and validate technical claims.

The goal is not simply fluent prose.

The draft should be:

- technically useful
- evidence-backed
- concrete
- opinionated where appropriate
- supported by realistic examples

---

## 3. Critique

The generated draft is evaluated by a separate critique stage.

The quality gate checks areas such as:

### Content

- minimum word count
- article structure
- concrete examples
- technical depth

### Technical Quality

- presence of real code
- concrete data
- factual claims
- references
- technical consistency

### AI-Writing Failure Modes

The critique also looks for:

- vague claims
- unsupported assertions
- plausible but broken code
- repetitive explanations
- unnecessary padding
- generic conclusions
- obvious AI-writing patterns

If the article fails the quality gate, it is sent back for revision.

The pipeline allows up to two revision rounds.

---

# ✨ Style & Voice

The final generation stage applies a dedicated style pass.

The style layer focuses on:

- clarity
- structure
- transitions
- tone
- specificity
- concise explanations
- stronger headings
- removal of unnecessary filler

The voice guidelines intentionally discourage common AI-writing patterns.

For example:

❌

> Let's dive into the fascinating world of AI agents.

Instead:

✅

> Most agent architectures fail for a surprisingly simple reason: they don't distinguish deterministic work from ambiguous work.

The goal is to make the article sound like **an engineer explaining something they actually understand**, rather than an LLM summarizing documentation.

---

# 👨‍💻 Human Review

Once the article passes all automated stages, BlogMind creates a GitHub Pull Request.

The PR acts as the final governance checkpoint.

The reviewer can validate:

- factual correctness
- technical accuracy
- personal experience
- code
- references
- article structure
- writing quality
- title and claims

Only after the PR is merged does the publishing workflow begin.

This is intentionally the **only mandatory human gate** in the core pipeline.

---

# 🚀 Publishing Pipeline

After the Pull Request is merged, a separate GitHub Actions workflow handles publishing.

Current destinations include:

### dev.to

Published through the dev.to REST API.

### Medium

The article can be imported from the canonical dev.to article using Medium's import workflow.

This remains a small semi-manual step because of Medium's platform/API constraints.

### LinkedIn

Publishing is handled through LinkedIn's Posts API.

OAuth authentication and token lifecycle management are part of the integration.

---

# ⚙️ Automation

BlogMind uses **GitHub Actions** for orchestration.

There are two major workflows:

```text
Generation Workflow
        ↓
Topic Discovery
        ↓
Content Generation
        ↓
Git Branch
        ↓
Pull Request


Publishing Workflow
        ↓
PR Merge
        ↓
Publish
        ↓
dev.to / Medium / LinkedIn
```

Separating the workflows means a publishing failure does not require regenerating the article.

---

# 🗂️ Project Structure

A simplified view of the repository structure:

```text
BlogMind/
│
├── .github/
│   └── workflows/
│       ├── generate.yml
│       └── publish.yml
│
├── src/
│   ├── discovery/
│   │   ├── arxiv.py
│   │   ├── hackernews.py
│   │   └── github.py
│   │
│   ├── generation/
│   │   ├── pipeline.py
│   │   ├── outline.py
│   │   ├── draft.py
│   │   ├── critique.py
│   │   └── style.py
│   │
│   ├── publishing/
│   │   ├── devto.py
│   │   ├── medium.py
│   │   └── linkedin.py
│   │
│   └── utils/
│
├── content/
│   ├── drafts/
│   ├── published/
│   └── .pipeline_state.json
│
├── scripts/
│   └── check_cadence.py
│
├── tests/
│
├── requirements.txt
└── README.md
```

> The exact structure may evolve as the project develops; the architecture above represents the logical separation of responsibilities.

---

# 🧰 Technology Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4.1 |
| AI Interface | OpenAI Responses API |
| Web Research | Hosted Web Search |
| Topic Discovery | arXiv Atom API |
|  | Hacker News Algolia API |
|  | GitHub Search API |
| Orchestration | GitHub Actions |
| Source Control | Git / GitHub |
| Review | GitHub Pull Requests |
| Content Format | Markdown + YAML Frontmatter |
| Publishing | dev.to REST API |
|  | Medium Import Story |
|  | LinkedIn Posts API |
| State Management | JSON |

---

# 🔐 Configuration

BlogMind relies on environment variables and GitHub Actions secrets for external integrations.

Typical configuration includes credentials for:

```text
OPENAI_API_KEY
DEVTO_API_KEY
LINKEDIN_ACCESS_TOKEN
```

Additional configuration can be used for:

```text
GITHUB_TOKEN
SITE_BASE_URL
```

Never commit API keys or access tokens to the repository.

For GitHub Actions, credentials should be stored using **GitHub Secrets**.

---

# 🚀 Getting Started

## Prerequisites

You should have:

- Python 3.x
- Git
- GitHub repository access
- OpenAI API access
- API credentials for any publishing platforms you want to enable

---

## Clone the Repository

```bash
git clone <your-repository-url>

cd BlogMind
```

---

## Create a Virtual Environment

```bash
python -m venv .venv
```

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a local environment configuration using the variables required by your enabled integrations.

For example:

```bash
export OPENAI_API_KEY="your-api-key"
```

Additional publisher credentials can be configured depending on which publishing destinations are enabled.

---

# ▶️ Running the Pipeline

The generation pipeline can be executed through the project's Python module entry point:

```bash
python -m src.generation.pipeline
```

For local development, it is important to test the **same invocation style used by CI**.

This matters because Python's import resolution can differ depending on whether a module is executed with:

```bash
python -m ...
```

or directly as:

```bash
python scripts/...
```

This distinction caused a real CI-only failure during development.

---

# 🧪 Testing

Run the project's test suite using the configured test runner.

For example:

```bash
pytest
```

Tests should cover:

- topic discovery
- scoring
- generation
- validation
- file handling
- publishing
- utility functions

---

# 🛡️ Reliability Engineering

One of the most important lessons from building BlogMind was that the biggest failures weren't necessarily AI failures.

They were **automation failures**.

Several production issues surfaced during development.

---

## Failed Writes Can Still Leave State Behind

A file opened in write mode can be created or truncated before the actual write operation succeeds.

Therefore:

> **A failed operation does not necessarily mean the system state is unchanged.**

The pipeline needs to account for partial state.

---

## Local Execution ≠ CI Execution

A command that works locally may fail under GitHub Actions because of:

- working directory
- Python import path
- environment variables
- shell behavior
- permissions
- available Git history

Always test the exact command used by the automation environment.

---

## Never Hide Process Exit Codes

Commands such as:

```bash
python pipeline.py | tail -n 1
```

can hide the actual exit status of the process you care about.

A workflow that reports green after a failed generation process is more dangerous than one that fails loudly.

The principle:

> **Every success signal must represent a meaningful success condition.**

---

## Prefer Ground Truth Over Inferred State

Git history isn't always a reliable representation of the current workspace.

Shallow clones, merge strategies, rebases, and workflow behavior can all make assumptions about `HEAD^` fragile.

If the required artifact is already present on disk, inspect the filesystem directly.

---

# 📊 State Management

BlogMind maintains pipeline state in:

```text
content/.pipeline_state.json
```

The state tracks information such as:

- last pipeline run
- content-pillar rotation
- scheduling information

This allows the scheduled workflow to remain deterministic while still using GitHub Actions' scheduled execution.

The state file is committed back into the repository as part of the workflow.

---

# 🧠 Why Human-in-the-Loop?

Full autonomy sounds attractive.

But content is different from deterministic software execution.

An AI can produce:

- a convincing anecdote
- a plausible benchmark
- a technically reasonable claim
- an experience written in first person

without knowing whether the author actually experienced it.

That is why BlogMind deliberately uses:

```text
AI Generation
      ↓
Automated Quality Checks
      ↓
Human Review
      ↓
Publication
```

The human is not there to manually operate the pipeline.

The human is there for **judgment**.

---

# 🔍 Key Engineering Lessons

### Separate probabilistic and deterministic work

Use the LLM where ambiguity and language understanding are required.

Use deterministic code for:

- file operations
- state management
- scheduling
- validation
- workflow control
- API orchestration

### Treat external APIs as architectural dependencies

Every platform has its own:

- authentication
- rate limits
- API lifecycle
- publishing model
- failure behavior

Design around those constraints instead of assuming uniform integrations.

### Make failures observable

A system that crashes loudly is inconvenient.

A system that silently stops working is dangerous.

The objective should be:

> **Make failures obvious and success meaningful.**

### Human review should be a feature, not a failure

A human checkpoint doesn't mean the automation failed.

It means the system understands where human judgment provides more value than another model call.

---

# 🗺️ Roadmap

- [ ] Additional content sources
- [ ] More sophisticated topic ranking
- [ ] Automated source credibility scoring
- [ ] Content performance analytics
- [ ] Article-level quality scoring
- [ ] Automated regression testing for generated code
- [ ] Improved retry and recovery strategies
- [ ] Additional publishing destinations
- [ ] Custom author/style profiles
- [ ] Historical topic deduplication
- [ ] Content performance feedback into topic selection
- [ ] Automated post-publication analytics
- [ ] More advanced observability for pipeline runs

---

# ⚠️ Important Notes

BlogMind is designed primarily as an **engineering project and experimentation platform** for AI-powered content automation.

Generated content should not be treated as automatically authoritative.

Human review remains an intentional part of the architecture.

External APIs and platform capabilities may change over time, so integrations should be treated as version-sensitive components.

---

# 🤝 Contributing

Contributions, ideas, and discussions are welcome.

If you want to contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Add or update tests where appropriate.
5. Open a Pull Request.
6. Describe the problem your change solves.

For larger architectural changes, open an issue first so the approach can be discussed before implementation.

---

# 📄 License

Add the project's chosen license here.

For example:

```text
MIT License
```

---

# 💬 Feedback

If you're building systems around:

- AI agents
- LLM orchestration
- content automation
- human-in-the-loop AI
- autonomous workflows
- AI-powered developer tooling

I'd love to hear how you're approaching the problem.

Especially this one:

> **What part of your AI workflow have you deliberately chosen not to automate?**

---

# ⭐ If You Find This Useful

If BlogMind gives you ideas for your own AI workflow, consider ⭐ starring the repository and sharing your feedback.

The goal isn't to build a system that blindly automates everything.

The goal is to build AI systems that are **useful, observable, reliable, and trustworthy.**

---

**BlogMind**

*From noisy signals to reviewed technical content — one pipeline at a time.*
