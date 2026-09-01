import pytest
from pydantic import BaseModel

from support_triage_agent.guardrails.output_guard import call_with_fallback
from support_triage_agent.guardrails.safety import SafetyBlockedError


class _Model(BaseModel):
    value: str


def test_returns_llm_result_and_no_flags_on_success() -> None:
    result, flags = call_with_fallback(lambda: "llm result", lambda: "fallback result")

    assert result == "llm result"
    assert flags == []


def test_falls_back_and_flags_schema_validation_failed_on_runtime_error() -> None:
    def failing_call():
        raise RuntimeError("Gemini returned an empty response.")

    result, flags = call_with_fallback(failing_call, lambda: "fallback result")

    assert result == "fallback result"
    assert flags == ["schema_validation_failed"]


def test_falls_back_and_flags_schema_validation_failed_on_validation_error() -> None:
    result, flags = call_with_fallback(
        lambda: _Model.model_validate({"not_value": "oops"}),
        lambda: "fallback result",
    )

    assert result == "fallback result"
    assert flags == ["schema_validation_failed"]


def test_falls_back_and_flags_safety_block_distinctly() -> None:
    def failing_call():
        raise SafetyBlockedError("blocked")

    result, flags = call_with_fallback(failing_call, lambda: "fallback result")

    assert result == "fallback result"
    assert flags == ["safety_block"]


def test_does_not_catch_unrelated_exceptions() -> None:
    def failing_call():
        raise KeyError("unrelated")

    with pytest.raises(KeyError):
        call_with_fallback(failing_call, lambda: "fallback result")
