"""
Guardrails applied before a user message reaches the LLM.

Two responsibilities, kept deliberately simple and deterministic (no LLM
call needed to guard the LLM call — that would add latency/cost and a new
failure mode):

1. Input validation — reject empty/oversized input and basic prompt-
   injection attempts (e.g. "ignore your previous instructions").
2. PII redaction — strip obvious PII patterns (email, phone, SSN-like,
   card-like numbers) from what gets logged, so structured logs (Step 5b)
   don't accidentally retain sensitive data even if a user pastes some.
   Redaction is applied to LOGS only, not to what's sent to the model —
   the agent still needs to see the real query to answer it.
"""
import re

MAX_INPUT_LENGTH = 2000

# Deliberately simple, keyword-based prompt-injection heuristic. This is
# NOT a robust defense (a determined attacker can phrase around it) — it's
# a first line of catching obvious/careless attempts, documented honestly
# rather than oversold. A production system would layer in a classifier.
_INJECTION_PATTERNS = [
    r"ignore (all |your )?(previous|prior|above) instructions",
    r"disregard (all |your )?(previous|prior|system) (instructions|prompt)",
    r"you are now (a|an) ",
    r"reveal your (system prompt|instructions)",
    r"act as (if you have no|an unrestricted)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def validate_input(text: str) -> tuple[bool, str | None]:
    """
    Returns (is_valid, reason). If is_valid is False, the caller should
    refuse to send `text` to the agent and surface `reason` to the user.
    """
    if not text or not text.strip():
        return False, "Empty message."

    if len(text) > MAX_INPUT_LENGTH:
        return False, (
            f"Message too long ({len(text)} chars, max {MAX_INPUT_LENGTH}). "
            f"Please shorten your question."
        )

    if _INJECTION_RE.search(text):
        return False, (
            "This message looks like it's trying to override my instructions "
            "rather than ask a financial research question. Please rephrase."
        )

    return True, None


# --- PII redaction (for logs only) ---

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def redact_pii(text: str) -> str:
    """Replace obvious PII patterns with a redaction marker. Log-only use."""
    text = _SSN_RE.sub("[REDACTED-SSN]", text)
    text = _CARD_RE.sub("[REDACTED-CARD]", text)
    text = _EMAIL_RE.sub("[REDACTED-EMAIL]", text)
    text = _PHONE_RE.sub("[REDACTED-PHONE]", text)
    return text
