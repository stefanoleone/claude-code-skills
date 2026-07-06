# How to use Claude Code skills

## What is a skill?

A skill is a directory whose `SKILL.md` file defines how Claude should approach a specific type of task, alongside any supporting files the skill needs at runtime (system prompts, helper scripts). `SKILL.md` includes:
- A trigger description (what kind of request activates it)
- A step-by-step execution protocol
- Output format and quality standards

Skills are loaded into Claude's context window before it responds, so it can follow the protocol reliably across sessions.

## Installing a skill

The repo is a [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) (see `.claude-plugin/marketplace.json`). Inside Claude Code:

```
/plugin marketplace add stefanoleone/claude-code-skills
/plugin install skills@claude-code-skills
```

This installs every skill in the collection as one plugin — each skill travels as a full directory (`SKILL.md` plus any helper scripts and system prompts it needs at runtime). Update with `/plugin marketplace update claude-code-skills`; the plugin declares no `version`, so every commit to `main` is a new version.

Claude will automatically detect and apply a skill when its trigger conditions match — no further configuration needed. You can also invoke one directly with its namespaced command, e.g. `/skills:reddit-sentiment-debate`.

## Triggering a skill

Skills are triggered by natural language. Each skill's README lists example phrases that activate it. You don't need to explicitly invoke a skill by name — Claude infers which one to use from your request.

## Creating your own skill

A minimal `SKILL.md` has two parts:

```markdown
---
name: your-skill-name
description: >
  One paragraph describing what the skill does and when Claude should use it.
  Include concrete trigger phrases ("Trigger when the user asks...").
---

# Your Skill Name

## Step 1: ...
## Step 2: ...
## Output format
...
```

The `description` field is what Claude reads to decide whether to apply the skill. Make it specific and include trigger phrases — this is what makes detection reliable.
