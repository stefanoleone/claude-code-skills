#!/usr/bin/env python3
"""Adversarial code review via any out-of-family LLM (OpenAI-compatible).

This is the *pure call layer* of the adversarial-pr-review skill. It does not
talk to GitHub, does not run git, and does not assemble context. Those concerns
belong to the SKILL.md orchestration, which pipes a fully-formed context payload
to this script over stdin (or via --context-file).

The reviewer model is deliberately meant to be from a DIFFERENT family than the
model that wrote the code (Claude reviewing Gemini's work, Gemini reviewing
Claude's, GPT reviewing either, ...). That out-of-family choice is the whole
point: same-family review shares blind spots. This script is model-agnostic on
purpose: any provider exposing an OpenAI-compatible endpoint works.

Pipeline: read context (stdin or --context-file) -> prepend system prompt ->
enforce an approximate token budget on the user payload -> call the provider ->
parse the hybrid markdown+JSON response -> emit per --output -> exit with a
verdict-encoded code.

Configuration (CLI flag overrides env; env is the convenient default):
    --provider   {anthropic,google,openai,openrouter}  fills a default base URL
    --base-url   OpenAI-compatible base URL   (env ADVREVIEW_BASE_URL)
    --model      reviewer model id            (env ADVREVIEW_MODEL)
    --api-key-env  name of the env var holding the key (default ADVREVIEW_API_KEY)
    --system-prompt  path to the system prompt (default: sibling adversarial_system.md)

Exit codes (deliberately shifted out of the 0-2 range so an unhandled exception
exiting 1 cannot be misread as `advisories_only`, and an argparse misuse exiting
2 cannot be misread as `blocker`; the orchestration keys on these values):
    100  verdict=clean
    101  verdict=advisories_only
    102  verdict=blocker
    103  schema validation failed (response did not match the contract)
    104  API / transport error (HTTP non-2xx, timeout, network)
    105  input / config error (no context, missing env, oversized after trim)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants

# Convenience presets so callers can pick a provider by name instead of
# memorizing base URLs. An explicit --base-url / ADVREVIEW_BASE_URL always wins.
# Verify against the provider's current docs — these endpoints evolve.
PROVIDER_BASE_URLS = {
    "anthropic": "https://api.anthropic.com/v1/",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

DEFAULT_API_KEY_ENV = "ADVREVIEW_API_KEY"

# The reviewer models run with large context windows; a generous budget keeps
# the whole branch in view. The count below is approximate (a char/4 heuristic
# when tiktoken is absent, cl100k_base when present) so it is a safety net, not
# a precise gate.
TIKTOKEN_ENCODING = "cl100k_base"
INPUT_TOKEN_BUDGET = 200_000

# Reasoning models (Gemini 3.x, o-series, ...) spend output tokens on hidden
# thinking before any visible text; a small cap can be consumed entirely by
# reasoning, yielding an empty response. Providers clamp to the model's own
# output limit, so a generous ceiling is safe where a tight one is not.
MAX_OUTPUT_TOKENS = 200_000

VALID_VERDICTS = {"clean", "advisories_only", "blocker"}
VERDICT_TO_EXIT = {"clean": 100, "advisories_only": 101, "blocker": 102}

EXIT_SCHEMA_FAIL = 103
EXIT_API_FAIL = 104
EXIT_INPUT_FAIL = 105

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "adversarial_system.md"

# Match an individual ```json ... ``` fenced block. The non-greedy `.*?`
# bounded by `\n```` matches one block at a time even with DOTALL. The parser
# picks the LAST match — the model may emit inline JSON examples earlier in the
# markdown (e.g. inside a `suggestion` field); the verdict payload is the
# trailing block.
JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)

VERDICT_HEADER_RE = re.compile(r"^##\s*Verdict\b.*$", re.IGNORECASE | re.MULTILINE)


# ---------------------------------------------------------------------------
# Helpers

@dataclass
class ReviewResult:
    """Parsed reviewer response."""
    verdict: str
    findings: list[dict]
    missed_requirements: list[dict]
    questions_for_author: list[str]
    markdown: str  # Full markdown body, JSON block stripped.
    raw: str       # Full unparsed reply, for --output json.


def _die(code: int, message: str, *, secret: str | None = None) -> None:
    """Print to stderr and exit with the given code.

    Redacts the resolved API key from any message before it reaches stderr —
    belt-and-suspenders to the per-call redaction in `_call_model`.
    """
    if secret and secret in message:
        message = message.replace(secret, "[REDACTED]")
    print(f"adversarial_review: {message}", file=sys.stderr)
    sys.exit(code)


def _read_context(args: argparse.Namespace) -> str:
    """Read the user-payload context from stdin or --context-file."""
    if args.context_file:
        path = Path(args.context_file)
        if not path.is_file():
            _die(EXIT_INPUT_FAIL, f"--context-file not found: {args.context_file}")
        return path.read_text(encoding="utf-8")
    if sys.stdin.isatty():
        _die(
            EXIT_INPUT_FAIL,
            "no context on stdin and no --context-file. "
            "This script is invoked by the adversarial-pr-review skill — "
            "did you mean the /adversarial-pr-review skill?",
        )
    return sys.stdin.read()


def _load_system_prompt(path: Path) -> str:
    """Read the system prompt.

    Read AFTER budget enforcement so the schema instructions can never be
    truncated away by the user-payload trim.
    """
    if not path.is_file():
        _die(EXIT_INPUT_FAIL, f"system prompt missing at {path}")
    return path.read_text(encoding="utf-8")


def _count_tokens(text: str) -> int:
    """Approximate token count.

    Uses cl100k_base if tiktoken is installed; otherwise a char/4 heuristic so
    the script has zero hard dependency beyond the `openai` SDK. The count is a
    safety net for oversized payloads, not a precise gate, so the heuristic is
    acceptable.
    """
    try:
        import tiktoken
    except ImportError:
        return len(text) // 4
    enc = tiktoken.get_encoding(TIKTOKEN_ENCODING)
    return len(enc.encode(text, disallowed_special=()))


def _enforce_budget(context: str, budget: int) -> str:
    """Truncate the user payload from the tail if it exceeds the budget.

    The skill assembles context with the order: repo canon -> PR (title/body/
    linked issue) -> diff -> changed files -> tests. The most-truncatable
    content (file bodies, tests) lives at the tail, so a character-proportional
    trim from the end preserves the load-bearing prefix. The skill owns
    ordering; this layer is the safety net.

    Inserts an explicit truncation marker so the reviewer knows context was
    clipped rather than fabricating findings about absent files.
    """
    actual = _count_tokens(context)
    if actual <= budget:
        return context
    ratio = budget / actual
    keep_chars = int(len(context) * ratio * 0.95)  # 5% safety margin
    trimmed = context[:keep_chars]
    marker = (
        f"\n\n---\n[TRUNCATED BY adversarial_review.py — original ~{actual:,} "
        f"tokens, trimmed to fit ~{budget:,}-token budget. File contents at the "
        f"tail of the context block were dropped. Treat absence of context as a "
        f"question_for_author, not a finding.]\n"
    )
    return trimmed + marker


def _resolve_config(args: argparse.Namespace) -> tuple[str, str, str]:
    """Resolve (base_url, model, api_key). Fail closed on any missing piece."""
    base_url = args.base_url or os.environ.get("ADVREVIEW_BASE_URL")
    if not base_url and args.provider:
        base_url = PROVIDER_BASE_URLS.get(args.provider)
    if not base_url:
        _die(
            EXIT_INPUT_FAIL,
            "no base URL: pass --base-url, set ADVREVIEW_BASE_URL, or pick "
            f"--provider from {sorted(PROVIDER_BASE_URLS)}.",
        )

    model = args.model or os.environ.get("ADVREVIEW_MODEL")
    if not model:
        _die(EXIT_INPUT_FAIL, "no model: pass --model or set ADVREVIEW_MODEL.")

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        _die(EXIT_INPUT_FAIL, f"{args.api_key_env} not set in environment")

    return base_url, model, api_key


def _call_model(
    system_prompt: str,
    user_context: str,
    *,
    base_url: str,
    model: str,
    api_key: str,
    timeout: float,
    max_tokens: int,
) -> str:
    """Single OpenAI-compatible call. Returns the raw reply string."""
    try:
        from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
    except ImportError as e:
        _die(EXIT_INPUT_FAIL, f"openai SDK missing: {e}. pip install openai")

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
    except (APIConnectionError, APITimeoutError) as e:
        _die(EXIT_API_FAIL, f"provider transport error: {type(e).__name__}", secret=api_key)
    except APIError as e:
        # Redact BEFORE truncating: a key straddling the 300-char cut would
        # survive _die's whole-string redaction.
        msg = str(e).replace(api_key, "[REDACTED]")
        _die(EXIT_API_FAIL, f"provider API error: {type(e).__name__}: {msg[:300]}", secret=api_key)
    except Exception as e:  # noqa: BLE001 — last-ditch barrier; never leak key
        _die(EXIT_API_FAIL, f"unexpected provider failure: {type(e).__name__}", secret=api_key)

    content = (resp.choices[0].message.content or "").strip()
    if not content:
        _die(EXIT_API_FAIL, "provider returned an empty response")
    return content


def _markdown_verdict(markdown: str) -> str | None:
    """Extract the verdict stated under the markdown `## Verdict` header.

    The search is confined to the Verdict section (up to the next `##`
    heading) so severity tags like `[blocker]` under `## Findings` cannot be
    mistaken for the verdict.
    """
    header = VERDICT_HEADER_RE.search(markdown)
    if not header:
        return None
    section = markdown[header.end():]
    next_heading = re.search(r"^##\s", section, re.MULTILINE)
    if next_heading:
        section = section[: next_heading.start()]
    word = re.search(r"\b(" + "|".join(sorted(VALID_VERDICTS)) + r")\b", section)
    return word.group(1) if word else None


def _parse_response(raw: str) -> ReviewResult:
    """Extract the JSON block and validate the schema."""
    matches = list(JSON_BLOCK_RE.finditer(raw))
    if not matches:
        _die(EXIT_SCHEMA_FAIL, "no ```json fenced block in the response")
    payload_match = matches[-1]

    try:
        data = json.loads(payload_match.group(1))
    except json.JSONDecodeError as e:
        _die(EXIT_SCHEMA_FAIL, f"JSON parse error: {e.msg} (line {e.lineno})")

    if not isinstance(data, dict):
        _die(EXIT_SCHEMA_FAIL, "JSON block is not an object")

    required = {"verdict", "findings", "missed_requirements", "questions_for_author"}
    missing = required - data.keys()
    if missing:
        _die(EXIT_SCHEMA_FAIL, f"JSON missing keys: {sorted(missing)}")

    verdict = data["verdict"]
    if verdict not in VALID_VERDICTS:
        _die(EXIT_SCHEMA_FAIL, f"invalid verdict {verdict!r}; expected one of {sorted(VALID_VERDICTS)}")

    for key in ("findings", "missed_requirements", "questions_for_author"):
        if not isinstance(data[key], list):
            _die(EXIT_SCHEMA_FAIL, f"`{key}` must be a list, got {type(data[key]).__name__}")

    # A blocker verdict must be backed by a blocker finding or a missed_requirement.
    if verdict == "blocker":
        has_blocker_finding = any(
            isinstance(f, dict) and f.get("severity") == "blocker"
            for f in data["findings"]
        )
        if not has_blocker_finding and not data["missed_requirements"]:
            _die(
                EXIT_SCHEMA_FAIL,
                "verdict=blocker but no blocker-severity finding and no missed_requirements",
            )

    # ...and the converse: any missed requirement forces a blocker verdict
    # (taxonomy in adversarial_system.md). A `clean` exit with unmet
    # requirements attached must never reach the caller as exit 100.
    if verdict != "blocker" and data["missed_requirements"]:
        _die(
            EXIT_SCHEMA_FAIL,
            f"verdict={verdict!r} but missed_requirements is non-empty "
            "(a missed requirement forces verdict=blocker)",
        )

    markdown = (raw[: payload_match.start()] + raw[payload_match.end():]).rstrip()

    # The markdown `## Verdict` section must agree with the JSON block; the
    # system prompt declares inconsistency a schema failure.
    md_verdict = _markdown_verdict(markdown)
    if md_verdict is None:
        _die(EXIT_SCHEMA_FAIL, "no verdict found under a markdown `## Verdict` header")
    if md_verdict != verdict:
        _die(
            EXIT_SCHEMA_FAIL,
            f"markdown verdict {md_verdict!r} does not match JSON verdict {verdict!r}",
        )
    return ReviewResult(
        verdict=verdict,
        findings=data["findings"],
        missed_requirements=data["missed_requirements"],
        questions_for_author=data["questions_for_author"],
        markdown=markdown,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# CLI

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adversarial_review",
        description=(
            "Adversarial code review via any out-of-family LLM (OpenAI-compatible). "
            "Pure call layer of the adversarial-pr-review skill — invoked with a "
            "fully-assembled context block on stdin."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes: 100 clean | 101 advisories_only | 102 blocker | "
            "103 schema fail | 104 API fail | 105 input/config fail.\n\n"
            "Reads the API key from the env var named by --api-key-env "
            f"(default {DEFAULT_API_KEY_ENV}). Never pass the key on the command line."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDER_BASE_URLS),
        help="Fills a default base URL for a known provider. Overridden by --base-url.",
    )
    parser.add_argument(
        "--base-url",
        help="OpenAI-compatible base URL. Env fallback: ADVREVIEW_BASE_URL.",
    )
    parser.add_argument(
        "--model",
        help="Reviewer model id. Env fallback: ADVREVIEW_MODEL.",
    )
    parser.add_argument(
        "--api-key-env",
        default=DEFAULT_API_KEY_ENV,
        help=f"Name of the env var holding the API key. Default: {DEFAULT_API_KEY_ENV}.",
    )
    parser.add_argument(
        "--system-prompt",
        default=str(DEFAULT_PROMPT_PATH),
        help="Path to the system prompt. Default: sibling adversarial_system.md.",
    )
    parser.add_argument(
        "--context-file",
        help="Path to a file with the assembled review context. If omitted, reads stdin.",
    )
    parser.add_argument(
        "--output",
        choices=("markdown", "json", "both"),
        default="both",
        help="What to print on stdout. Default: both (markdown then fenced JSON).",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=INPUT_TOKEN_BUDGET,
        help=f"User-payload token budget (approximate). Default: {INPUT_TOKEN_BUDGET}.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=MAX_OUTPUT_TOKENS,
        help=(
            "Max output tokens for the review (reasoning models spend these on "
            f"hidden thinking too). Default: {MAX_OUTPUT_TOKENS}."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Provider request timeout in seconds. Default: 300.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    base_url, model, api_key = _resolve_config(args)

    context = _read_context(args)
    if not context.strip():
        _die(EXIT_INPUT_FAIL, "context is empty")

    context = _enforce_budget(context, args.budget)
    system_prompt = _load_system_prompt(Path(args.system_prompt))
    raw = _call_model(
        system_prompt,
        context,
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
    )
    result = _parse_response(raw)

    if args.output in ("markdown", "both"):
        print(result.markdown)
    if args.output == "both":
        print()  # Spacer between markdown and machine-parseable JSON.
    if args.output in ("json", "both"):
        payload = {
            "verdict": result.verdict,
            "findings": result.findings,
            "missed_requirements": result.missed_requirements,
            "questions_for_author": result.questions_for_author,
        }
        print(json.dumps(payload, indent=2))

    return VERDICT_TO_EXIT[result.verdict]


if __name__ == "__main__":
    sys.exit(main())
