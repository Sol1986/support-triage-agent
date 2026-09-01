from support_triage_agent.guardrails.safety import SafetyBlockedError
from support_triage_agent.llm import (
    ClassificationResult,
    ResponseResult,
)
from support_triage_agent.nodes import (
    classify_ticket,
    draft_response,
    revise_response,
)


class FakeLLMService:
    model = "fake-gemini"

    def classify_ticket(
        self,
        ticket_text: str,
    ) -> ClassificationResult:
        return ClassificationResult(category="billing")

    def draft_response(
        self,
        ticket_text: str,
        category: str,
        priority: str,
    ) -> ResponseResult:
        return ResponseResult(
            response=(
                "We received your billing request and assigned it "
                "high priority. A specialist will review it."
            )
        )

    def revise_response(
        self,
        ticket_text: str,
        category: str,
        priority: str,
        current_response: str,
        feedback: str,
    ) -> ResponseResult:
        return ResponseResult(
            response=(
                "We received your billing request. As a next step, "
                "a specialist will review it. Keep your reference "
                "number available."
            )
        )


def test_llm_classification(base_state, monkeypatch):
    fake_service = FakeLLMService()

    monkeypatch.setattr(
        "support_triage_agent.nodes.get_llm_service",
        lambda: fake_service,
    )

    base_state["llm_enabled"] = True

    result = classify_ticket(base_state)

    assert result["category"] == "billing"


def test_llm_draft(base_state, monkeypatch):
    fake_service = FakeLLMService()

    monkeypatch.setattr(
        "support_triage_agent.nodes.get_llm_service",
        lambda: fake_service,
    )

    base_state["llm_enabled"] = True
    base_state["category"] = "billing"
    base_state["priority"] = "high"

    result = draft_response(base_state)

    assert "billing" in result["draft_response"]
    assert result["revision_count"] == 0


def test_llm_revision(base_state, monkeypatch):
    fake_service = FakeLLMService()

    monkeypatch.setattr(
        "support_triage_agent.nodes.get_llm_service",
        lambda: fake_service,
    )

    base_state["llm_enabled"] = True
    base_state["category"] = "billing"
    base_state["priority"] = "high"
    base_state["draft_response"] = "Incomplete response"
    base_state["evaluation_feedback"] = "Missing next step and reference number."

    result = revise_response(base_state)

    assert "As a next step" in result["draft_response"]
    assert "reference number" in result["draft_response"]
    assert result["revision_count"] == 1


class _FailingLLMService:
    """Simulates a Gemini call that fails its structured-output guardrail."""

    model = "fake-gemini"

    def __init__(self, exception: Exception) -> None:
        self._exception = exception

    def classify_ticket(self, ticket_text: str):
        raise self._exception

    def draft_response(self, ticket_text: str, category: str, priority: str):
        raise self._exception

    def revise_response(
        self,
        ticket_text: str,
        category: str,
        priority: str,
        current_response: str,
        feedback: str,
    ):
        raise self._exception


def test_classify_ticket_falls_back_to_keywords_on_schema_failure(
    base_state, monkeypatch
):
    monkeypatch.setattr(
        "support_triage_agent.nodes.get_llm_service",
        lambda: _FailingLLMService(RuntimeError("empty response")),
    )

    base_state["llm_enabled"] = True
    base_state["ticket_text"] = "I was charged twice for my subscription."

    result = classify_ticket(base_state)

    assert result["category"] == "billing"
    assert result["schema_validation_failed"] is True
    assert "schema_validation_failed" in result["guardrail_flags"]


def test_draft_response_falls_back_to_template_on_safety_block(base_state, monkeypatch):
    monkeypatch.setattr(
        "support_triage_agent.nodes.get_llm_service",
        lambda: _FailingLLMService(SafetyBlockedError("blocked")),
    )

    base_state["llm_enabled"] = True
    base_state["category"] = "billing"
    base_state["priority"] = "high"

    result = draft_response(base_state)

    assert "billing" in result["draft_response"]
    assert "safety_block" in result["guardrail_flags"]
    # A safety block is a distinct flag from a schema-validation failure.
    assert result["schema_validation_failed"] is False


def test_revise_response_falls_back_to_template_on_schema_failure(
    base_state, monkeypatch
):
    monkeypatch.setattr(
        "support_triage_agent.nodes.get_llm_service",
        lambda: _FailingLLMService(RuntimeError("empty response")),
    )

    base_state["llm_enabled"] = True
    base_state["category"] = "billing"
    base_state["priority"] = "high"
    base_state["draft_response"] = "Incomplete response"
    base_state["evaluation_feedback"] = "Missing next step and reference number."

    result = revise_response(base_state)

    assert "As a next step" in result["draft_response"]
    assert result["schema_validation_failed"] is True
