---
name: adversarial-pr-review
metadata:
  author: Stefano Leone
  linkedin: "https://www.linkedin.com/in/stefanoleone"
  created: 2026-07-03
description: >
  Adversarial second-opinion code review of the current pull request, run by an
  LLM from a DIFFERENT model family than the one that wrote the code. Same-family
  review (the coding agent reviewing its own work) shares blind spots; this skill
  breaks that echo chamber by handing the PR to a configurable out-of-family
  reviewer (Anthropic Opus, Google Gemini, OpenAI GPT, or anything on OpenRouter)
  and surfacing a strict verdict (clean / advisories_only / blocker) with findings
  and missed requirements. Optionally pulls the ticket / acceptance criteria from a
  Plane, Linear, or Jira MCP server (or a linked GitHub issue) so the reviewer checks
  the diff against the actual contract. Trigger whenever the user asks to "adversarially review
  this PR", "get a second opinion on this branch", "review my PR with a different
  model", "have Gemini/Opus/GPT review this", "out-of-family code review", or wants
  an independent model to check a pull request before merge. Also trigger for:
  "cross-check this diff with another model", "run adversarial review".
---

# Adversarial PR Review

Get a code review of the current pull request from a model of a **different family** than the one that wrote the code. If Claude Code wrote the branch, have Gemini or GPT review it. If Google Antigravity (Gemini) wrote it, have Opus review it. The point is to escape the blind spots a model shares with itself.

This skill is the **context + orchestration layer**. It detects the PR, assembles the review context, and hands it to `scripts/adversarial_review.py` (the **call layer**, which talks to the reviewer model over an OpenAI-compatible endpoint and returns a strict verdict). You surface that verdict verbatim.

---

## Step 0: Resolve the reviewer model

The reviewer must be a **different family** than whatever wrote the code under review. That is the user's judgment call — you cannot always know the code's author — so confirm it.

Resolve configuration in this priority order:

1. **Environment already set?** If `ADVREVIEW_MODEL` **and** (`ADVREVIEW_BASE_URL` or a known provider) **and** the API key env var are all present, use them. Tell the user which model you'll use and let them override.
2. **Otherwise ask the user** which model should do the review. Offer the common presets and remind them to pick a family different from the code's author:

   | Provider | `--provider` | `--base-url` | example `--model` | key env |
   |---|---|---|---|---|
   | Anthropic | `anthropic` | `https://api.anthropic.com/v1/` | `claude-opus-4-8` | `ADVREVIEW_API_KEY` |
   | Google | `google` | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3-pro` | `ADVREVIEW_API_KEY` |
   | OpenAI | `openai` | `https://api.openai.com/v1` | `gpt-5.1` | `ADVREVIEW_API_KEY` |
   | OpenRouter | `openrouter` | `https://openrouter.ai/api/v1` | `anthropic/claude-opus-4.8` | `ADVREVIEW_API_KEY` |

   (Model ids drift — confirm the exact id against the provider's current catalog.)

3. **Verify the API key is set.** The key lives in the env var named by `--api-key-env` (default `ADVREVIEW_API_KEY`). If it is not exported, abort and tell the user to export it. **Never pass the key on the command line** (it would leak into shell history and process lists) and never echo its value.

If you (the orchestrating model) are from the **same family** as the reviewer the user picked, gently flag it: "Heads up — you asked me (Claude) to also review with a Claude model, so this isn't out-of-family. Want Gemini or GPT instead?" Then proceed if they confirm.

## Step 1: Detect the pull request

Requires the GitHub CLI (`gh`) authenticated for the repo.

```bash
gh pr view --json number,title,body,headRefName,baseRefName,url,state
```

- If a PR exists for the current branch, use it.
- If **no PR exists**, tell the user. Offer to review the working diff against the default branch instead (`git diff origin/main...HEAD` — substitute the actual base). Do not silently invent a PR.
- If the branch is at parity with the base (empty diff), abort with a one-line message; do not run a degraded review.

## Step 1b: Fetch the ticket / linked issue (the contract's source of truth)

The **contract** the reviewer checks the diff against is the PR body plus, if there is one, the ticket or issue behind it. Resolve it from whichever source is available, in this order:

1. **A ticket-system MCP server**, if the host has one connected. Infer the ticket id from the PR body (`Closes ABC-123`, `Fixes LIN-42`), the branch name (e.g. `feat/ABC-123-...`), or ask the user. Then fetch it via the MCP whose tools are exposed in this session:
   - **Plane** — `mcp__plane__retrieve_work_item_by_identifier` (pass `fields=...` and `expand="assignees,labels"`; without `expand`, some Plane shims raise a validation error).
   - **Linear** — `mcp__linear__*` (e.g. `get_issue`).
   - **Jira / Atlassian** — `mcp__*Atlassian*` issue tools.
   - Any other ticket MCP that can fetch an issue by id works the same way.

   Strip HTML from the description before including it. Confirm the inferred id with the user before calling MCP; do not invent one.
2. **A linked GitHub issue** (no MCP needed) if the PR body references `#N`:
   ```bash
   gh issue view <N> --json title,body
   ```
3. **Neither** — fall back to the PR body alone, and note in the context that no external ticket was available so the reviewer reviews against the PR description + diff only.

The skill uses whatever MCP the host already has; it does not ship one. If no ticket MCP is configured, that is fine — the GitHub-issue and PR-body paths cover the common case.

## Step 2: Assemble the context block

Build a single markdown block in **this exact order** (the script's token-budget safety net trims from the tail, so put the least-droppable content first):

### 1. Repo canon (never truncate)

If any of these exist at the repo root, read and include them under a `## Repo canon` header: `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `README.md`. These teach the reviewer the project's own conventions so it cites them instead of generic best practices. If none exist, skip this section — the reviewer will fall back to the diff and general judgment.

### 2. Pull request + ticket (never truncate)

Under `## Pull request`, include the PR title and body. Then, under `## Ticket (contract)`, include the ticket or linked issue fetched in Step 1b (title + description + acceptance criteria), or an explicit "no external ticket available" note. Together these are the contract the reviewer maps `missed_requirements` against.

### 3. Diff (never truncate)

```bash
gh pr diff        # or: git diff <base>...HEAD
```

Wrap under a `## Diff` header.

### 4. Changed files (truncatable)

For every file in `gh pr diff --name-only` (or `git diff --name-only <base>...HEAD`):

- If the file exists on the branch: read its full content.
- If it was deleted: include just the path + a `# DELETED` marker.

Order files by **changed-line count descending** so that, if truncation fires, the least-modified files drop first. Wrap each under a `### path/to/file` header.

### 5. Test output (optional, truncatable)

If tests were run in this session and the summary is in scrollback, append a `## Test output` section with pass/fail counts + any failure tracebacks. If unsure, skip it.

## Step 3: Call the reviewer

Write the assembled context to a temp file (preferred for large branches, avoids shell-argument limits) and invoke the script. Pass the model config via flags; the key stays in the environment.

```bash
python3 skills/adversarial-pr-review/scripts/adversarial_review.py \
  --provider anthropic \
  --model claude-opus-4-8 \
  --context-file /tmp/adv_review_context.md \
  --output both
```

(Substitute the resolved provider/model. Use `--base-url` instead of `--provider` for a custom endpoint. Adjust the script path to where the skill is installed.)

Run it in the **foreground** with a generous timeout — the call can take 60-300s on a large branch. Do not background it.

The script exits with:

| Exit | Meaning | What to surface |
|---|---|---|
| 100 | `clean` | "The reviewer concurs — no blockers, no advisories." |
| 101 | `advisories_only` | List the advisories. Note they are non-blocking. |
| 102 | `blocker` | List blockers + missed requirements prominently. Recommend not merging until resolved. |
| 103 | Schema failure | The response didn't parse. Show the raw output; offer to re-run. |
| 104 | API failure | Provider unreachable / errored. Show the redacted error. Do not auto-retry; surface it. |
| 105 | Input/config error | Usually a missing key or model/base-url. Surface the cause and ask. |

Any other non-zero exit (typically 1 or 2) means the script crashed — surface stderr and offer to re-run; do **not** treat it as a verdict.

## Step 4: Surface the verdict

Present a concise summary:

1. **Verdict** in bold (clean / advisories_only / blocker), naming which model produced it.
2. **Findings** — render the script's markdown section verbatim. Do not summarize away severity tags or file paths.
3. **Missed requirements** — verbatim.
4. **Questions for the author** — verbatim. These are for the user to answer, not for you to answer on the reviewer's behalf.
5. **Recommendation** — one sentence: e.g. "Verdict `clean` — safe to merge." or "Verdict `blocker` — address the missed requirement before merge."

Do **not** re-review the findings from your own perspective or overrule the reviewer. The entire value of this skill is surfacing an out-of-family opinion as-is. If you disagree, say so as a clearly-labeled separate note — do not contaminate the adversarial verdict.

## Hard rules

1. **Never echo or log the API key.** Reference it only via the environment. The script redacts it from provider-error messages; do not undo that.
2. **Never pass the key on the command line.** It goes in the env var named by `--api-key-env`.
3. **Fail closed on missing context.** No PR and no working diff, empty diff, or unresolvable model config → abort with a one-line message. Do not run a degraded review.
4. **Read-only on the working tree.** This is a review tool; do not edit the changed files.
5. **The reviewer's verdict is the reviewer's.** Surface it verbatim; the user decides what to do with it.
