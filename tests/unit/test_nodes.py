import pytest

from support_triage_agent.nodes import (
    assign_priority,
    classify_ticket,
    evaluate_response,
    revise_response,
    validate_ticket,
)
from support_triage_agent.state import TicketState


@pytest.mark.parametrize(
    ("ticket_text", "expected_category"),
    [
        (
            "I was charged twice for my subscription.",
            "billing",
        ),
        (
            "The application crashes when I log in.",
            "technical",
        ),
        (
            "I need to change my account profile.",
            "account",
        ),
        (
            "My package delivery has not arrived.",
            "shipping",
        ),
        (
            "I would like information about your company.",
            "general",
        ),
    ],
)
def test_classify_ticket(
    base_state: TicketState,
    ticket_text: str,
    expected_category: str,
) -> None:
    base_state["ticket_text"] = ticket_text

    result = classify_ticket(base_state)

    assert result["category"] == expected_category


def test_validate_ticket_removes_whitespace(
    base_state: TicketState,
) -> None:
    base_state["ticket_text"] = "   I need assistance with my account.   "

    result = validate_ticket(base_state)

    assert result["ticket_text"] == ("I need assistance with my account.")


@pytest.mark.parametrize(
    "ticket_text",
    [
        "",
        "      ",
        "Help",
    ],
)
def test_validate_ticket_rejects_invalid_input(
    base_state: TicketState,
    ticket_text: str,
) -> None:
    base_state["ticket_text"] = ticket_text

    with pytest.raises(ValueError):
        validate_ticket(base_state)


def test_assigns_high_priority(
    base_state: TicketState,
) -> None:
    base_state["ticket_text"] = "I was charged twice and need help immediately."
    base_state["category"] = "billing"

    result = assign_priority(base_state)

    assert result["priority"] == "high"
    assert result["requires_human_review"] is True


def test_billing_requires_human_review(
    base_state: TicketState,
) -> None:
    base_state["ticket_text"] = "I have a question about an invoice."
    base_state["category"] = "billing"

    result = assign_priority(base_state)

    assert result["priority"] == "low"
    assert result["requires_human_review"] is True


def test_first_draft_fails_evaluation(
    base_state: TicketState,
) -> None:
    base_state["category"] = "billing"
    base_state["draft_response"] = "We received your billing support request."

    result = evaluate_response(base_state)

    assert result["evaluation_score"] == 6
    assert "needs improvement" in result["evaluation_feedback"]


def test_revision_passes_evaluation(
    base_state: TicketState,
) -> None:
    base_state["category"] = "billing"
    base_state["priority"] = "high"

    revision = revise_response(base_state)
    base_state.update(revision)

    evaluation = evaluate_response(base_state)

    assert base_state["revision_count"] == 1
    assert evaluation["evaluation_score"] == 10
