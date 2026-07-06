# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A curated collection of Claude Code skills — structured prompt-engineering artifacts, not an application. There is no build system, test suite, or linter. The deliverables are the `SKILL.md` files under `skills/`; most changes are documentation edits, and the only executable code is one Python script.

## Repository layout

Each skill lives at `skills/<skill-name>/` and contains:

- `SKILL.md` — the installable artifact. YAML frontmatter (`name`, `metadata` with `author`/`linkedin`/`created`, `description`) followed by a step-by-step execution protocol. The `description` field is what makes skill detection work: it must state when to trigger and include concrete trigger phrases ("Trigger whenever the user asks..."). Quote the LinkedIn URL in frontmatter (unquoted URLs broke YAML parsing before).
- `README.md` — human-facing docs: what it does, example triggers, output structure, install pointer back to the main README.
- Optional supporting files (scripts, system prompts) when the skill orchestrates external tooling.

When adding or renaming a skill, also update the skills table in the root `README.md` and the plugin `description` in `.claude-plugin/marketplace.json`. `docs/how-to-use.md` documents the generic install/authoring flow.

## Distribution

The repo is a Claude Code plugin marketplace: `.claude-plugin/marketplace.json` declares a single plugin named `skills` with `source: "./"`, so every directory under `skills/` is auto-discovered as a skill of that plugin (install: `/plugin marketplace add stefanoleone/claude-code-skills`, then `/plugin install skills@claude-code-skills`). The plugin deliberately declares no `version`: versioning rides on git commit SHAs, so every commit to `main` reaches users on `/plugin marketplace update` — do not add a `version` field without adopting a release process.

## adversarial-pr-review architecture

The one skill with real code, deliberately split into two layers:

- **`SKILL.md` (orchestration layer)** — detects the PR via `gh`, fetches the ticket/linked issue (the "contract"), assembles the context block in a fixed order (repo canon → PR + ticket → diff → changed files → test output; least-truncatable first), and surfaces the verdict verbatim.
- **`scripts/adversarial_review.py` (call layer)** — pure and model-agnostic: reads assembled context from stdin or `--context-file`, calls any OpenAI-compatible endpoint, parses the hybrid markdown+JSON response, exits with a verdict-encoded code. It never touches git/GitHub and never assembles context.
- **`adversarial_system.md`** — the reviewer model's system prompt, loaded by the script. Defines the output schema and verdict taxonomy.

Exit codes are shifted out of the 0–2 range on purpose (so a crash exiting 1 can't be misread as a verdict): 100 clean, 101 advisories_only, 102 blocker, 103 schema failure, 104 API failure, 105 input/config error.

**Cross-file contract:** the verdict taxonomy, JSON schema, and exit-code table are duplicated across `adversarial_system.md`, `adversarial_review.py` (`VALID_VERDICTS`, `VERDICT_TO_EXIT`, `_parse_response`), `SKILL.md`, and the skill's `README.md`. A change to any of these must be propagated to all four files.

**Security invariants:** the API key is read only from an env var (default `ADVREVIEW_API_KEY`), never accepted on the command line, and redacted from error output (`_die`'s `secret` parameter). Preserve this in any change.

## Running the script

Python 3.11+; the only hard dependency is `openai` (`tiktoken` optional — improves token counting from a char/4 heuristic to exact).

```bash
export ADVREVIEW_API_KEY=sk-...
python3 skills/adversarial-pr-review/scripts/adversarial_review.py \
  --provider anthropic --model claude-opus-4-8 \
  --context-file /path/to/context.md --output both
```

`--provider {anthropic,google,openai,openrouter}` fills a default base URL; `--base-url` overrides it. There are no automated tests — verify changes by running the script against a small context file and checking the exit code (`echo $?`).

## Commit style

Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`.
