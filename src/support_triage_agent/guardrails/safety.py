"""Gemini safety configuration for generated content.

`llm.py` passes `get_gemini_safety_settings()` into every `generate_content`
call; `is_safety_blocked()` and `SafetyBlockedError` let it distinguish a
safety block from an ordinary empty/malformed response, so the guardrail
layer can flag it distinctly for the escalation policy (see `policy.py`).
"""

from typing import Any

from google.genai import types

_BLOCKED_HARM_CATEGORIES = (
    types.HarmCategory.HARM_CATEGORY_HARASSMENT,
    types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
)


class SafetyBlockedError(RuntimeError):
    """Raised when Gemini blocks a generation on safety grounds.

    Subclasses `RuntimeError` so any caller only interested in "the LLM call
    failed" (e.g. `guardrails.output_guard.call_with_fallback`'s broad
    except) still catches it; callers that need to tell a safety block apart
    from an ordinary schema failure can catch this type specifically.
    """


def get_gemini_safety_settings() -> list[types.SafetySetting]:
    """Block medium-and-above risk content across Gemini's standard harm categories."""
    return [
        types.SafetySetting(
            category=category,
            threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        )
        for category in _BLOCKED_HARM_CATEGORIES
    ]


def is_safety_blocked(response: Any) -> bool:
    """Whether Gemini blocked generation on safety grounds rather than returning content."""
    candidates = getattr(response, "candidates", None) or []

    return any(
        getattr(candidate, "finish_reason", None) == types.FinishReason.SAFETY
        for candidate in candidates
    )
