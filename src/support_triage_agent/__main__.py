import json

from support_triage_agent.nodes import (
    assign_priority,
    classify_ticket,
    create_summary,
    draft_response,
    validate_ticket,
)
from support_triage_agent.state import TicketState


def process_ticket(ticket_text: str) -> TicketState:
    state = TicketState(ticket_text=ticket_text)

    state = validate_ticket(state)
    state = classify_ticket(state)
    state = assign_priority(state)
    state = create_summary(state)
    state = draft_response(state)

    return state

if __name__ == "__main__":
    result = process_ticket("My package did not arrive and I have a delivery problem.")
    print(json.dumps(result.to_dict(), indent=2))