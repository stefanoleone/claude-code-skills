# Adversarial PR Review

Get a second opinion on your pull request from an LLM of a **different model family** than the one that wrote the code.

When a coding agent reviews its own work, it shares its own blind spots. This skill breaks that echo chamber: it hands the current PR to a configurable, out-of-family reviewer and returns a strict verdict with findings and missed requirements.

- Wrote the branch with **Claude Code**? Review it with **Gemini** or **GPT**.
- Wrote it with **Google Antigravity** (Gemini)? Review it with **Opus**.
- Any provider with an OpenAI-compatible endpoint works — you pick the model.

This is the differentiator over the built-in `/review` and `/code-review` commands: those run the *same* model that wrote the code. This one is deliberately a *different* model.

---

## Example triggers

- "Adversarially review this PR"
- "Get a second opinion on this branch from a different model"
- "Have Gemini review this pull request before I merge"
- "Review my PR with GPT and check it against the ticket"
- "Run adversarial review"

## What a run looks like

```text
> Adversarially review this PR

⏺ Detected PR #42 "Add rate limiting to the ingest API"
⏺ Found linked ticket ENG-311 — pulling acceptance criteria into the contract
⏺ Reviewer: gemini-3-pro (out-of-family — this branch was written by Claude)

**Verdict: `blocker`** — reviewer: gemini-3-pro

Findings:
- [blocker] api/ingest.py L88 — the retry loop re-enters the handler above
  the limiter, so a failing client bypasses rate limiting entirely.
- [minor] api/config.py L12 — new setting is undocumented in settings.md.

Missed requirements:
- "Limits must be configurable per API key" → the limit is a module-level
  constant; no per-key configuration exists in the diff.

Questions for the author:
- How should burst traffic be handled when Redis is unavailable?

Recommendation: do not merge until the blocker and the missed requirement
are resolved.
```

| Section | Content |
|---|---|
| Verdict | `clean` / `advisories_only` / `blocker`, naming the reviewer model |
| Findings | severity-tagged issues with file/line and a concrete suggestion |
| Missed requirements | gaps mapped to specific PR/ticket requirements |
| Questions for the author | ambiguities the reviewer could not resolve from context |
| Recommendation | one line: merge or don't merge |

---

## How it works

Two layers:

- **`SKILL.md`** — orchestration. Detects the PR (`gh`), reads the PR body + linked issue (the "contract"), assembles diff + changed files + repo canon, and surfaces the verdict.
- **`scripts/adversarial_review.py`** — the call layer. Talks to the reviewer model over an OpenAI-compatible endpoint, enforces a token budget, parses the hybrid markdown+JSON response, and exits with a verdict-encoded code.

The reviewer emits a strict schema; the script maps it to exit codes:

| Exit | Verdict |
|---|---|
| 100 | `clean` — merge as-is |
| 101 | `advisories_only` — non-blocking notes |
| 102 | `blocker` — a blocker finding or an unmet PR requirement |
| 103 | schema failure (response didn't parse) |
| 104 | API / transport failure |
| 105 | input / config error |

A non-empty `missed_requirements` array always forces `blocker` — an unmet PR requirement is a blocker regardless of code quality.

---

## Requirements

- [`gh`](https://cli.github.com/) — GitHub CLI, authenticated for the repo.
- Python 3.11+ with the `openai` SDK: `pip install openai` (the only hard dependency).
- `tiktoken` is **optional** — if installed, token budgeting is exact; if not, a char/4 heuristic is used.
- An API key for the reviewer provider.

---

## Configuration

The script reads config from CLI flags (which override env vars). The API key is **always** read from an environment variable and never passed on the command line.

| What | Flag | Env fallback |
|---|---|---|
| Provider preset | `--provider {anthropic,google,openai,openrouter}` | — |
| Base URL (overrides preset) | `--base-url` | `ADVREVIEW_BASE_URL` |
| Model id | `--model` | `ADVREVIEW_MODEL` |
| API key (name of the env var) | `--api-key-env` (default `ADVREVIEW_API_KEY`) | — |

### Provider presets

| Provider | `--provider` | base URL | example model |
|---|---|---|---|
| Anthropic | `anthropic` | `https://api.anthropic.com/v1/` | `claude-opus-4-8` |
| Google | `google` | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3-pro` |
| OpenAI | `openai` | `https://api.openai.com/v1` | `gpt-5.1` |
| OpenRouter | `openrouter` | `https://openrouter.ai/api/v1` | `anthropic/claude-opus-4.8` |

Endpoints and model ids evolve — verify against each provider's current docs. **OpenRouter** is the most flexible: one key, switch models by changing `--model`.

### Example

```bash
export ADVREVIEW_API_KEY=sk-...        # the reviewer provider's key

# Review the current PR with Opus (e.g. code written by Gemini):
python3 scripts/adversarial_review.py --provider anthropic --model claude-opus-4-8 \
  --context-file /tmp/context.md

# ...or with Gemini (e.g. code written by Claude):
python3 scripts/adversarial_review.py --provider google --model gemini-3-pro \
  --context-file /tmp/context.md
```

In normal use you don't build the context yourself — invoke the skill and let `SKILL.md` assemble it.

---

## The contract: give the adversary your ticket

The single highest-leverage thing you can do for review quality is feeding the reviewer the **contract** — the ticket or issue that says what the branch was *supposed* to do.

Without it, the adversary can only judge code quality: it sees a diff and tells you whether the code is well built. With it, it also judges **completeness**: every acceptance criterion becomes a checkable requirement, and anything the diff doesn't deliver comes back as a `missed_requirements` entry — which alone forces a `blocker` verdict. "Technically clean but doesn't do what was asked" is exactly the failure class a same-family self-review waves through, and it is only catchable if the reviewer knows what was asked. Two practical consequences:

- **Link the ticket where the skill can find it** — `Closes ABC-123` / `Fixes #42` in the PR body, or the ticket id in the branch name (`feat/ABC-123-rate-limit`).
- **Write testable acceptance criteria.** The reviewer maps `missed_requirements` against them verbatim; vague tickets produce vague reviews.

Sources, in priority order:

1. **A ticket-system MCP server** connected to your coding agent — Plane (`mcp__plane__*`), Linear (`mcp__linear__*`), or Jira/Atlassian (`mcp__*Atlassian*`). The skill infers the ticket id from the PR body or branch name, confirms it, and fetches title + description + acceptance criteria.
2. **A linked GitHub issue** (`Closes #N` in the PR body) via `gh issue view` — no MCP needed.
3. **Neither** — the PR body alone is the contract, and the reviewer is told no external ticket was available.

### Setting up access

The skill uses whatever the **host agent** already has configured; it does not bundle an MCP server or any credential of its own. One-time setup per source (commands are for Claude Code — any MCP-capable agent works; endpoints evolve, check each provider's docs):

| Source | Setup |
|---|---|
| **Plane** | Connect Plane's MCP server with an API token from your workspace settings, e.g. `claude mcp add plane -- npx -y @makeplane/plane-mcp-server` with `PLANE_API_KEY` and workspace slug in the env. |
| **Linear** | `claude mcp add --transport http linear https://mcp.linear.app/mcp`, then authenticate via OAuth (`/mcp` in Claude Code). |
| **Jira / Atlassian** | `claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/sse`, then authenticate via OAuth. |
| **GitHub issues** | No MCP — `gh auth login` once; the skill reads linked issues with `gh issue view`. |

Ticket fetching lives entirely in the orchestration layer (`SKILL.md`) — the Python call layer only ever sees the assembled contract as text, so no script config or dependency is involved.

---

## Install

See the [installation instructions](../../README.md#how-to-use-these-skills) in the main README. One caveat specific to this skill: it ships a helper script and a system prompt alongside `SKILL.md`, so copy the **whole directory**, not a single file:

```bash
# project-level
cp -r skills/adversarial-pr-review .claude/skills/

# or user-level (available in every project)
cp -r skills/adversarial-pr-review ~/.claude/skills/
```

Then invoke it with any of the [example triggers](#example-triggers) above.

---

## Design notes

- **Out-of-family is the user's call.** The skill can't always know what wrote the code, so it asks you to pick a reviewer from a different family and flags the obvious same-family case.
- **The PR is the contract.** The reviewer checks the diff against the PR description + linked issue, not just against code quality. An unmet requirement is a blocker.
- **Fail closed.** Missing key, no PR/diff, empty diff, or unparseable response → abort or a script-level error code, never a fabricated "clean".
- **Secret hygiene.** The key is env-only and redacted from any error message.
