from support_triage_agent.graph import support_graph
from support_triage_agent.state import TicketState


def process_ticket(ticket_text: str) -> TicketState:
    initial_state = {
        "ticket_text": ticket_text,
        "category": "",
        "priority": "",
        "summary": "",
        "draft_response": "",
        "evaluation_score": 0,
        "evaluation_feedback": "",
        "revision_count": 0,
        "requires_human_review": False,
    }

    final_state = support_graph.invoke(initial_state)

    return final_state