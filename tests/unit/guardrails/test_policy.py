from support_triage_agent.guardrails.policy import evaluate_escalation
from support_triage_agent.state import MAX_REVISIONS, TicketState


def _state(**overrides) -> TicketState:
    defaults: TicketState = {
        "ticket_text": "My invoice shows an incorrect amount.",
        "category": "billing",
        "priority": "low",
        "summary": "",
        "draft_response": "",
        "evaluation_score": 10,
        "evaluation_feedback": "",
        "revision_count": 0,
        "requires_human_review": False,
        "llm_enabled": False,
        "model_used": "deterministic-rules",
        "guardrail_flags": [],
        "escalation_reason": None,
        "initial_evaluation_score": 10,
        "schema_validation_failed": False,
    }
    defaults.update(overrides)
    return defaults


def test_routine_ticket_does_not_escalate() -> None:
    decision = evaluate_escalation(_state(), [])

    assert decision.requires_human_review is False
    assert decision.matched_rules == []


def test_account_compromise_language_escalates() -> None:
    state = _state(
        ticket_text="I think someone else has logged into my account, I did not request this."
    )

    decision = evaluate_escalation(state, [])

    assert decision.requires_human_review is True
    assert "account_compromise" in decision.matched_rules


def test_fraud_language_escalates() -> None:
    state = _state(ticket_text="I did not authorize this purchase on my account.")

    decision = evaluate_escalation(state, [])

    assert decision.requires_human_review is True
    assert "fraud" in decision.matched_rules


def test_threat_language_escalates() -> None:
    state = _state(ticket_text="Someone is threatening me over this dispute.")

    decision = evaluate_escalation(state, [])

    assert "threat" in decision.matched_rules


def test_legal_language_escalates() -> None:
    state = _state(
        ticket_text="I am going to pursue legal action if this is not resolved."
    )

    decision = evaluate_escalation(state, [])

    assert "legal_complaint" in decision.matched_rules


def test_payment_card_info_escalates() -> None:
    state = _state(ticket_text="My card number and CVV were charged incorrectly.")

    decision = evaluate_escalation(state, [])

    assert "payment_card_info" in decision.matched_rules


def test_injection_flag_escalates() -> None:
    decision = evaluate_escalation(_state(), ["injection_suspected"])

    assert "prompt_injection_suspected" in decision.matched_rules


def test_repeated_evaluation_failure_escalates() -> None:
    state = _state(revision_count=MAX_REVISIONS, evaluation_score=6)

    decision = evaluate_escalation(state, [])

    assert "repeated_evaluation_failure" in decision.matched_rules


def test_max_revisions_reached_with_good_score_does_not_escalate() -> None:
    state = _state(revision_count=MAX_REVISIONS, evaluation_score=10)

    decision = evaluate_escalation(state, [])

    assert "repeated_evaluation_failure" not in decision.matched_rules


def test_schema_validation_failure_flag_escalates() -> None:
    decision = evaluate_escalation(_state(), ["schema_validation_failed"])

    assert "schema_validation_failed" in decision.matched_rules


def test_safety_block_flag_escalates() -> None:
    decision = evaluate_escalation(_state(), ["safety_block"])

    assert "safety_block" in decision.matched_rules


def test_reason_reflects_first_matched_rule() -> None:
    decision = evaluate_escalation(
        _state(ticket_text="I did not authorize this purchase."), []
    )

    assert decision.reason == "Possible fraud or unauthorized charge"
