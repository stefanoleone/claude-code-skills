# How to use Claude Code skills

## What is a skill?

A skill is a `SKILL.md` file that defines how Claude should approach a specific type of task. It includes:
- A trigger description (what kind of request activates it)
- A step-by-step execution protocol
- Output format and quality standards

Skills are loaded into Claude's context window before it responds, so it can follow the protocol reliably across sessions.

## Installing a skill

1. Find the skill folder you want (e.g., `skills/reddit-sentiment-debate/`)
2. Copy the `SKILL.md` file to your Claude Code skills directory:

```bash
# Replace <skill-name> with the folder name
cp skills/<skill-name>/SKILL.md /mnt/skills/user/<skill-name>/SKILL.md
```

3. Claude will automatically detect and apply it when the trigger conditions match — no further configuration needed.

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
