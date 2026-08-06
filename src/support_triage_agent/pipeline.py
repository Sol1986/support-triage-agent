from support_triage_agent.config import (
    get_gemini_model,
    is_llm_enabled,
)
from support_triage_agent.graph import support_graph
from support_triage_agent.state import TicketState


def process_ticket(ticket_text: str) -> TicketState:
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
        "model_used": (
            get_gemini_model()
            if llm_enabled
            else "deterministic-rules"
        ),
    }

    final_state = support_graph.invoke(initial_state)

    return final_state