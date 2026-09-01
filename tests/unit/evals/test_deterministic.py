from support_triage_agent.evals import deterministic
from support_triage_agent.evals.models import GoldenExample
from support_triage_agent.state import TicketState


def _example(**overrides) -> GoldenExample:
    defaults = {
        "id": "TEST-01",
        "ticket_text": "I was charged twice for my subscription.",
        "expected_category": "billing",
        "expected_priority": "high",
        "expected_requires_human_review": False,
        "tags": ["billing"],
    }
    defaults.update(overrides)
    return GoldenExample.model_validate(defaults)


def _state(**overrides) -> TicketState:
    defaults: TicketState = {
        "ticket_text": "I was charged twice for my subscription.",
        "category": "billing",
        "priority": "high",
        "summary": "",
        "draft_response": "",
        "evaluation_score": 10,
        "evaluation_feedback": "Response meets all required quality checks.",
        "revision_count": 1,
        "requires_human_review": False,
        "llm_enabled": False,
        "model_used": "deterministic-rules",
    }
    defaults.update(overrides)
    return defaults


def test_category_accuracy_passes_on_match() -> None:
    result = deterministic.category_accuracy(_example(), _state(category="billing"))

    assert result.passed is True


def test_category_accuracy_fails_on_mismatch() -> None:
    result = deterministic.category_accuracy(_example(), _state(category="technical"))

    assert result.passed is False


def test_priority_accuracy_fails_on_mismatch() -> None:
    result = deterministic.priority_accuracy(_example(), _state(priority="low"))

    assert result.passed is False


def test_high_priority_recall_skipped_when_not_expected_high() -> None:
    result = deterministic.high_priority_recall(
        _example(expected_priority="low"), _state(priority="low")
    )

    assert result is None


def test_high_priority_recall_fails_when_missed() -> None:
    result = deterministic.high_priority_recall(
        _example(expected_priority="high"), _state(priority="medium")
    )

    assert result is not None
    assert result.passed is False


def test_schema_compliance_defaults_to_passed_without_the_flag() -> None:
    # `_state()` never sets `schema_validation_failed` (it's added by Phase 2's
    # output guardrail), so this exercises the `.get()` fallback path.
    result = deterministic.schema_compliance(_example(), _state())

    assert result.passed is True


def test_required_response_elements_reuses_evaluation_score() -> None:
    result = deterministic.required_response_elements(
        _example(), _state(evaluation_score=6)
    )

    assert result.passed is False


def test_human_escalation_accuracy_fails_on_mismatch() -> None:
    result = deterministic.human_escalation_accuracy(
        _example(expected_requires_human_review=True),
        _state(requires_human_review=False),
    )

    assert result.passed is False
