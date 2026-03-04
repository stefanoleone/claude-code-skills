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

### Option 1: Install from GitHub (quickest)

Run `/install-skill` inside Claude Code and paste the GitHub URL to the `SKILL.md` file you want to install (e.g. `https://github.com/stefanoleone/claude-code-skills/blob/main/skills/reddit-sentiment-debate/SKILL.md`).

### Option 2: Manual install (project-level)

Copy the `SKILL.md` file into your project's `.claude/commands/` directory:

```
.claude/commands/SKILL.md
```

The skill will be available as a slash command when working in that project.

### Option 3: Manual install (global)

Place the `SKILL.md` file in `~/.claude/commands/` to make it available across all your projects:

```
~/.claude/commands/SKILL.md
```

---

## About

Built by [Stefano Leone](https://github.com/stefanoleone) — AI Product Manager at IO Group, startup mentor, and advisor.

These skills reflect real workflows at the intersection of product management, AI tooling, and blockchain development.

If you're building AI-native product workflows and want to exchange ideas, feel free to open an issue or connect.
