---
name: reddit-sentiment-debate
metadata:
  author: Stefano Leone
  created: 2026-03-01
description: >
  Sentiment-driven market analysis skill that mines Reddit communities to understand how a specific persona perceives a product or feature, then runs a structured PRO vs. AGAINST agent debate grounded in real community data, and produces a ranked minimum feature list to convert skeptics. Trigger whenever the user asks "Would [persona] be interested in [product/feature]?", "What would it take to convince [audience] to adopt [X]?", "What are the blockers for [user type] to buy [product]?", or wants persona-driven Reddit sentiment analysis, product-market fit research, market validation, or a debate between advocates and skeptics. Also trigger for: "run a sentiment analysis on Reddit about X", "what does Reddit think about Y", "debate pros and cons of Z for [persona]".
---

# Reddit Sentiment Debate

This skill turns a simple question ("Would <persona> be interested in <product>?") into a structured, evidence-based analysis: Reddit intelligence → agent debate → minimum feature list.

The output is actionable: not "people seem interested", but "here are the 4 specific things that would convert a skeptic".

---

## Step 0: Extract inputs

From the user's message, identify:
- **Persona**: who we're analyzing (e.g., "backend engineer", "privacy-conscious user", "small business owner")
- **Product/Feature**: what we're evaluating (e.g., "GitHub Copilot", "WhatsApp payment features", "Shopify AI tools")

If either is ambiguous, ask before proceeding.

---

## Step 1: Reddit intelligence gathering

Since the Reddit API requires approval for access, use web search with `site:reddit.com` to gather community sentiment. This gives you authentic, unfiltered user perspectives.

Run these searches in parallel to get broad coverage:

1. `site:reddit.com [persona] [product]` — general overlap
2. `site:reddit.com [product] review OR experience OR thoughts` — general sentiment
3. `site:reddit.com [product] hate OR problem OR issue OR disappointed` — objections and pain points
4. `site:reddit.com [product] love OR great OR switched OR recommend` — advocates and wins
5. `site:reddit.com r/[persona-relevant-subreddit] [product]` — persona's own community (infer the most relevant subreddit from the persona, e.g. r/webdev for developers, r/smallbusiness for business owners)

For each search result, extract:
- The actual user statements (what people say, not just titles)
- Recurring themes across multiple posts/comments
- Specific features or missing features that are mentioned
- The emotional tone (frustrated, enthusiastic, indifferent)

Aim for at least 10-15 distinct data points before moving on. If initial searches are sparse, try alternative search terms.

---

## Step 2: Synthesize findings

Before the debate, organize what you've found into two clear camps. This is the raw material both agents will draw from.

**PRO signals** (reasons the persona would be interested):
- List specific benefits mentioned on Reddit
- Note which pain points the product solves that this persona actually has
- Highlight any viral moments, success stories, or enthusiastic testimonials

**AGAINST signals** (reasons the persona would resist):
- List specific objections, frustrations, dealbreakers
- Note missing features that were requested
- Highlight trust issues, pricing concerns, workflow friction, ethical objections

Present this synthesis to the user before the debate, formatted clearly. Label it **"Reddit Intelligence Summary"**. This step is important — it shows the user where the debate data comes from and lets them spot anything missing.

---

## Step 3: The debate

Now instantiate two agents and run them through a structured debate. Both agents are grounded entirely in the Reddit intelligence from Step 2 — no speculation, no generic claims.

**PRO agent**: Advocates for the product from the perspective of what genuinely benefits the persona. They argue based on real use cases and documented wins. They also propose specific features or changes to address AGAINST's objections.

**AGAINST agent**: Represents the skeptical persona. They raise concrete objections grounded in Reddit evidence. They are not a strawman — they are a reasonable, thoughtful person who has seen the criticism and isn't convinced yet. They shift position only when a specific objection is genuinely addressed.

**Debate format** (up to 5 rounds):

> Round N:
> PRO: [argument or response to AGAINST's last point, proposes feature/change if needed]
> AGAINST: [raises or maintains specific objection, or concedes a point if genuinely addressed]
> Status: [which objections remain unresolved]

**Convergence rules**:
- AGAINST concedes a point only when PRO has proposed something that directly addresses it with enough specificity
- The debate ends when either: (a) AGAINST is fully convinced, (b) 5 rounds pass, or (c) a clear stalemate is reached on specific points
- Don't force artificial resolution — a stalemate is a valid and informative outcome

Render the debate as a readable dialogue, not as a list of bullet points. It should feel like a real exchange.

---

## Step 4: Output — minimum feature list

After the debate, produce the final deliverable: **what would it actually take to convert the AGAINST persona?**

Structure the output as:

### Minimum feature set to convert a skeptic

For each feature/change:
- **What**: the specific thing needed
- **Why it matters**: the exact objection it resolves (tied to Reddit evidence)
- **Priority**: Must-have / Nice-to-have

Rank by impact — the top items are the ones AGAINST was most insistent about.

Also include a short **Verdict** paragraph: given the current state of the product (before any hypothetical changes), would most members of this persona adopt it? Be direct.

---

## Output format summary

Your final response should have four labeled sections:

1. **Reddit Intelligence Summary** — PRO and AGAINST signals from community data
2. **The Debate** — the dialogue between PRO and AGAINST agents
3. **Minimum Feature List** — ranked table of what would convert a skeptic
4. **Verdict** — a direct, honest assessment of current product-market fit for this persona

Keep the tone analytical and honest. Don't oversell the product or the method. If Reddit data is sparse for a niche product, say so — it's meaningful signal that the community hasn't formed strong opinions yet.
