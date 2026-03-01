# Reddit Sentiment Debate

A Claude Code skill for evidence-based market validation using Reddit community data.

## What it does

Takes a simple question — *"Would [persona] be interested in [product]?"* — and turns it into a structured, three-stage analysis:

1. Reddit intelligence gathering (web search with `site:reddit.com`)
2. Structured PRO vs. AGAINST agent debate grounded in real community data
3. Ranked minimum feature list: what it would actually take to convert a skeptic

## When to use it

- Validating product-market fit for a specific persona before building
- Understanding adoption blockers before a launch or pitch
- Structuring user research when you don't have time for interviews
- Preparing for objections in a product review or investor conversation

## Example triggers

- "Would Cardano developers be interested in a formal verification IDE plugin?"
- "What would it take to convince privacy-conscious users to adopt a cloud password manager?"
- "Run a Reddit sentiment analysis on Cursor for senior engineers"
- "Debate pros and cons of GitHub Copilot for backend developers"

## Output structure

| Section | Content |
|---|---|
| Reddit Intelligence Summary | PRO and AGAINST signals extracted from community posts |
| The Debate | Dialogue between PRO and AGAINST agents (up to 5 rounds) |
| Minimum Feature List | Ranked table of what would convert the skeptic |
| Verdict | Direct, honest assessment of current product-market fit |

## How to install

Copy `SKILL.md` to your Claude Code skills directory:

```bash
cp SKILL.md /mnt/skills/user/reddit-sentiment-debate/SKILL.md
```

Claude will automatically detect and apply the skill when the trigger conditions match.

---

Author: Stefano Leone · Created: 2026-03-01
