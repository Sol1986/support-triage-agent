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
    base_state["evaluation_feedback"] = (
        "Missing next step and reference number."
    )

    result = revise_response(base_state)

    assert "As a next step" in result["draft_response"]
    assert "reference number" in result["draft_response"]
    assert result["revision_count"] == 1