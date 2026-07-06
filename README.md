# Claude Code Skills

A curated collection of custom skills for [Claude Code](https://claude.ai/code), built from real product and research workflows.

Each skill is a structured prompt engineering artifact that teaches Claude how to approach a specific type of task — reliably, step by step, with actionable outputs.

---

## What is a Claude skill?

A Claude Code skill is a `SKILL.md` file that defines:
- When the skill should be triggered (description + trigger phrases)
- A step-by-step execution protocol
- Output format and quality standards

Skills are loaded into Claude's context to guide behavior for specific, recurring workflows. Think of them as reusable SOP templates for AI-native work.

---

## Skills in this repository

| Skill | Description | Use case |
|---|---|---|
| [reddit-sentiment-debate](./skills/reddit-sentiment-debate/) | Reddit intelligence → agent debate → minimum feature list | Product-market fit research, persona validation |
| [adversarial-pr-review](./skills/adversarial-pr-review/) | Second-opinion PR review by an out-of-family model (Opus / Gemini / GPT / OpenRouter) | Catch what the coding agent's own self-review misses before merge |

---

## How to use these skills

This repo is a [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces): each skill is its own plugin, so you install only what you need. Inside Claude Code:

```
/plugin marketplace add stefanoleone/claude-code-skills
/plugin install adversarial-pr-review@claude-code-skills
/plugin install reddit-sentiment-debate@claude-code-skills
```

Add the marketplace once, then install any subset — or browse the catalog interactively with `/plugin`. Each skill travels as a full directory (`SKILL.md` plus any helper scripts and system prompts it needs at runtime) and triggers automatically on the phrases in its description.

To pick up updates later, run `/plugin marketplace update claude-code-skills` — every commit to `main` is a new version.

---

## About

Built by [Stefano Leone](https://github.com/stefanoleone) — AI Product Manager at IO Group, startup mentor, and advisor.

These skills reflect real workflows at the intersection of product management, AI tooling, and blockchain development.

If you're building AI-native product workflows and want to exchange ideas, feel free to open an issue or connect.
