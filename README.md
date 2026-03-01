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

---

## How to use these skills

1. Copy the `SKILL.md` file from any skill folder
2. Place it in your Claude Code skills directory: `/mnt/skills/user/<skill-name>/SKILL.md`
3. Claude will automatically detect and apply it when the trigger conditions match

---

## About

Built by [Stefano Leone](https://github.com/stefanoleone) — Senior Product Manager at IOHK / Input Output, working on the Cardano High Assurance Initiative.

These skills reflect real workflows at the intersection of product management, AI tooling, and blockchain development.

If you're building AI-native product workflows and want to exchange ideas, feel free to open an issue or connect.
