import pytest

from support_triage_agent.state import TicketState


@pytest.fixture
def base_state() -> TicketState:
    return {
        "ticket_text": "I was charged twice for my subscription.",
        "category": "",
        "priority": "",
        "summary": "",
        "draft_response": "",
        "evaluation_score": 0,
        "evaluation_feedback": "",
        "revision_count": 0,
        "requires_human_review": False,
        "llm_enabled": False,
        "model_used": "deterministic-rules",
        "guardrail_flags": [],
        "escalation_reason": None,
        "initial_evaluation_score": 0,
        "schema_validation_failed": False,
    }


@pytest.fixture(autouse=True)
def disable_external_services(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("DATABASE_ENABLED", "false")
