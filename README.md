# Agentic AI Blog Automation

An end-to-end pipeline that sources emerging Agentic AI topics, drafts technical
blog posts using Claude, routes them through a human review gate, and publishes
to your own site, dev.to (→ Medium via Import Story), and LinkedIn — on a
2-day cadence.

```
Topic Sourcing → Topic Scoring → Outline → Draft → Critique → Style Pass
      → Human Review (GitHub PR) → Publish (site + dev.to + LinkedIn)
```

## Repo layout

```
config/
  pillars.yaml          # the 5 content pillars + rotation logic
  settings.yaml          # cadence, model, thresholds
src/
  sourcing/              # pulls candidate topics from arxiv, HN, GitHub trending
  generation/             # the multi-pass Claude drafting pipeline
  review/                 # opens a GitHub PR with the draft for human approval
  publishing/              # dev.to + LinkedIn publishers, Medium helper
  utils/                  # Claude API client, storage helpers
content/
  drafts/                 # generated drafts land here pre-approval
  published/               # approved, published posts (source of truth, Markdown)
.github/workflows/
  generate-draft.yml       # runs every 2 days: sources topic, drafts, opens PR
  publish.yml               # runs on PR merge: publishes everywhere
```

## Setup

1. **Clone and install**
   ```bash
   pip install -r requirements.txt
   cp .env.example .env   # fill in secrets
   ```

2. **Required secrets** (set as GitHub Actions repo secrets, and locally in `.env`):
   | Secret | Used for |
   |---|---|
   | `ANTHROPIC_API_KEY` | Claude drafting pipeline |
   | `DEVTO_API_KEY` | Publishing to dev.to |
   | `LINKEDIN_ACCESS_TOKEN` | Posting to LinkedIn (see LinkedIn setup below) |
   | `LINKEDIN_PERSON_URN` | Your LinkedIn member URN, e.g. `urn:li:person:XXXX` |
   | `GH_TOKEN` | Token with repo scope, used by the Action to open PRs |

3. **LinkedIn setup** (one-time, manual):
   - Create an app at https://www.linkedin.com/developers/apps
   - Add the "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect" products
   - Run the OAuth flow once (see `src/publishing/linkedin_oauth_helper.py`) to get a
     refresh token — LinkedIn access tokens expire in 60 days, so you'll need to
     refresh periodically. This repo includes a helper script; full OAuth consent
     screens can't be automated end-to-end since LinkedIn requires a real browser login.

4. **Medium**: Medium closed new API integrations in 2023. This pipeline publishes
   to dev.to programmatically, then you (or a light script) trigger Medium's
   **Import a Story** tool (`medium.com/p/import`) with the dev.to URL. This is the
   one step that stays manual/semi-manual — `src/publishing/medium_helper.py` prints
   the exact URL to paste in, and even opens the tab for you if run locally.

5. **Your own site**: This repo treats `content/published/*.md` as the source of
   truth. Point an Astro or Next.js site's content collection at this folder (or
   sync it into that repo) to render it as your canonical blog.

## Running locally

```bash
# 1. Source + score topics, generate a draft
python -m src.generation.pipeline

# 2. Review the draft in content/drafts/, edit if needed

# 3. Publish an approved draft
python -m src.publishing.publish_all content/published/2026-08-14-example.md
```

## How the schedule works

`.github/workflows/generate-draft.yml` runs on a cron every 2 days. It:
1. Picks the next pillar in rotation (`config/pillars.yaml`)
2. Sources candidate topics for that pillar
3. Scores them with Claude, picks the best
4. Runs the drafting pipeline (outline → draft → critique → style)
5. Commits the draft to `content/drafts/` and opens a PR

You review the PR (edit inline if needed). Merging it to `main` triggers
`.github/workflows/publish.yml`, which moves the file to `content/published/`
and calls the publishers.
