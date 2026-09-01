"""Regex-based PII detection for logs and traces.

Not a full NLP-based detector — a real PII library (e.g. Presidio) would
catch more, at the cost of a new dependency; see docs/EVALS_GUARDRAILS_PLAN.md
§12 for that tradeoff. `detect_pii` feeds the escalation policy (payment-card
detection) and `guard_output`'s flags; `redact` is for text that is about to
reach a log line or trace payload — never the customer-facing response
itself, since redacting a customer's own PII out of their own response is
usually wrong.
"""

import re

_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(
        r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ),
    "card_number": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


def detect_pii(text: str) -> list[str]:
    """Names of the PII categories found in `text`, if any."""
    return [name for name, pattern in _PATTERNS.items() if pattern.search(text)]


def redact(text: str) -> str:
    """Replace detected PII with a `[REDACTED_<TYPE>]` placeholder."""
    redacted = text

    for name, pattern in _PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED_{name.upper()}]", redacted)

    return redacted
