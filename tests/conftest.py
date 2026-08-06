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
    }


@pytest.fixture(autouse=True)
def disable_external_services(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("DATABASE_ENABLED", "false")
