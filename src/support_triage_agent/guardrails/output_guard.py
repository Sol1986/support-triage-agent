"""Guardrail wrapper around Gemini's structured-output calls.

`llm.py`'s methods already force `response_schema` and raise on an empty or
safety-blocked response; this is the layer that decides what happens when
that raising occurs in production — fall back to the deterministic path and
flag it, rather than letting an unhandled exception reach the API layer.
"""

from collections.abc import Callable
from typing import TypeVar

from pydantic import ValidationError

from support_triage_agent.guardrails.safety import SafetyBlockedError

T = TypeVar("T")


def call_with_fallback(
    llm_call: Callable[[], T],
    fallback: Callable[[], T],
) -> tuple[T, list[str]]:
    """Run `llm_call`; on a structured-output or safety failure, run `fallback` instead.

    Returns `(result, flags)` — `flags` is `["safety_block"]`,
    `["schema_validation_failed"]`, or `[]` on success — so the caller can
    record the right guardrail flag on `TicketState` without re-deriving it.
    """
    try:
        return llm_call(), []
    except SafetyBlockedError:
        return fallback(), ["safety_block"]
    except (RuntimeError, ValidationError):
        return fallback(), ["schema_validation_failed"]
