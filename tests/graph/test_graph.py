import pytest

from support_triage_agent.graph import support_graph
from support_triage_agent.pipeline import process_ticket
from support_triage_agent.state import TicketState


def test_complete_graph_processes_billing_ticket() -> None:
    result = process_ticket("I was charged twice and need a refund immediately.")

    assert result["category"] == "billing"
    assert result["priority"] == "high"
    assert result["evaluation_score"] == 10
    assert result["revision_count"] == 1
    assert result["requires_human_review"] is True


def test_graph_follows_revision_route(
    base_state: TicketState,
) -> None:
    events = list(
        support_graph.stream(
            base_state,
            stream_mode="updates",
        )
    )

    executed_nodes = [next(iter(event)) for event in events]

    assert executed_nodes.count("evaluate_response") == 2
    assert executed_nodes.count("revise_response") == 1
    assert executed_nodes[-1] == "evaluate_response"


def test_graph_rejects_empty_ticket() -> None:
    with pytest.raises(ValueError):
        process_ticket("")


def test_shipping_ticket_uses_shipping_route() -> None:
    result = process_ticket("My package delivery has not arrived.")

    assert result["category"] == "shipping"
    assert result["evaluation_score"] == 10


def test_technical_issue_receives_medium_priority() -> None:
    result = process_ticket("My application is not working and I need help soon.")

    assert result["category"] == "technical"
    assert result["priority"] == "medium"
    assert result["requires_human_review"] is True
