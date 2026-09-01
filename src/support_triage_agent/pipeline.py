from support_triage_agent.config import (
    get_gemini_model,
    is_llm_enabled,
)
from support_triage_agent.graph import support_graph
from support_triage_agent.state import TicketState


def process_ticket(ticket_text: str) -> TicketState:
    """Run a raw ticket string through the triage graph and return the final state.

    This is the single entry point used by both the API layer and the CLI, so
    the initial-state shape only has to be assembled correctly in one place.
    """
    llm_enabled = is_llm_enabled()

    initial_state: TicketState = {
        "ticket_text": ticket_text,
        "category": "",
        "priority": "",
        "summary": "",
        "draft_response": "",
        "evaluation_score": 0,
        "evaluation_feedback": "",
        "revision_count": 0,
        "requires_human_review": False,
        "llm_enabled": llm_enabled,
        "model_used": (get_gemini_model() if llm_enabled else "deterministic-rules"),
        "guardrail_flags": [],
        "escalation_reason": None,
        "initial_evaluation_score": 0,
        "schema_validation_failed": False,
    }

    final_state = support_graph.invoke(initial_state)

    return final_state
