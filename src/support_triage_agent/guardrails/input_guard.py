"""Input guardrail for the triage graph, run as the `guard_input` node.

`nodes.validate_ticket` already rejects (via `ValueError`) empty or under-10-
character ticket text, and `models.TicketRequest` enforces length bounds at
the API boundary — this module deliberately does not duplicate either check,
to avoid changing that existing, already-tested rejection behavior. What it
adds is new: rejecting structurally garbled (mostly non-printable) text, and
flagging — but never blocking on — suspected prompt-injection attempts,
since ticket text must always be treated as untrusted data, not instructions
(see also the untrusted-data framing in `llm.py`'s prompts).
"""

import re

from pydantic import BaseModel, Field

# Patterns suggestive of an attempt to redirect the system away from treating
# ticket text as data. These only ever set a flag for the escalation policy
# to weigh — never a hard block — since legitimate tickets can innocently
# contain words like "ignore" or "instructions".
_INJECTION_PATTERNS = [
    re.compile(
        r"\bignore\s+(your\s+|the\s+|all\s+)?(previous|prior|above)\s+instructions?\b",
        re.IGNORECASE,
    ),
    re.compile(r"\breveal\s+(your\s+)?system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\b(return|output)\s+priority\s+\w+\s+regardless\b", re.IGNORECASE),
    re.compile(
        r"\boutput\s+\w+\s+instead\s+of\s+the\s+(requested\s+)?schema\b", re.IGNORECASE
    ),
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(
        r"\bdisregard\s+(your\s+|the\s+)?(instructions|prompt|rules)\b", re.IGNORECASE
    ),
]

_MIN_PRINTABLE_RATIO = 0.5


class InputGuardResult(BaseModel):
    """Outcome of screening a raw ticket before it enters the triage graph."""

    accepted: bool
    flags: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None


def check_input(ticket_text: str) -> InputGuardResult:
    """Structural screening beyond `nodes.validate_ticket`'s emptiness/length check."""
    stripped = ticket_text.strip()

    if stripped:
        printable_ratio = sum(character.isprintable() for character in stripped) / len(
            stripped
        )
        if printable_ratio < _MIN_PRINTABLE_RATIO:
            return InputGuardResult(
                accepted=False,
                rejection_reason="Ticket text is mostly non-printable characters.",
            )

    flags = []
    if any(pattern.search(stripped) for pattern in _INJECTION_PATTERNS):
        flags.append("injection_suspected")

    return InputGuardResult(accepted=True, flags=flags)
