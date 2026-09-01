from support_triage_agent.evals import llm_judge
from support_triage_agent.evals.harness import run_evaluators
from support_triage_agent.evals.metrics import compute_metrics
from support_triage_agent.evals.models import EvaluatorResult, GoldenExample
from support_triage_agent.state import TicketState


def _example() -> GoldenExample:
    return GoldenExample.model_validate(
        {
            "id": "TEST-01",
            "ticket_text": "I was charged twice for my subscription.",
            "expected_category": "billing",
            "expected_priority": "high",
            "expected_requires_human_review": False,
            "tags": ["billing"],
        }
    )


def _state() -> TicketState:
    return {
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


def test_run_evaluators_runs_only_deterministic_evaluators_by_default(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_JUDGE_ENABLED", "false")

    result = run_evaluators(_example(), _state(), latency_ms=1.0)

    evaluator_names = {
        evaluator.evaluator_name for evaluator in result.evaluator_results
    }
    assert evaluator_names == {
        "category_accuracy",
        "priority_accuracy",
        "high_priority_recall",
        "schema_compliance",
        "required_response_elements",
        "human_escalation_accuracy",
    }
    assert all(
        evaluator.kind == "deterministic" for evaluator in result.evaluator_results
    )


def test_run_evaluators_records_revision_trace() -> None:
    result = run_evaluators(_example(), _state(), latency_ms=1.0)

    assert result.revision_trace.revision_count == 1
    assert result.revision_trace.final_score == 10


def test_compute_metrics_handles_a_single_perfect_run() -> None:
    result = run_evaluators(_example(), _state(), latency_ms=1.0)

    metrics = compute_metrics([result])

    assert metrics.example_count == 1
    assert metrics.category_accuracy == 1.0
    assert metrics.priority_accuracy == 1.0
    assert metrics.human_escalation_accuracy == 1.0
    assert metrics.response_completeness_rate == 1.0
    assert metrics.average_response_quality is None
    assert metrics.hallucination_rate is None


def test_compute_metrics_handles_no_runs() -> None:
    metrics = compute_metrics([])

    assert metrics.example_count == 0
    assert metrics.category_accuracy is None
    assert metrics.first_pass_success_rate is None


def test_run_evaluators_includes_judge_results_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("LLM_JUDGE_ENABLED", "true")
    monkeypatch.setattr(
        llm_judge,
        "run_judge_evaluators",
        lambda example, actual: [
            EvaluatorResult(evaluator_name="helpfulness", kind="llm_judge", score=5.0)
        ],
    )

    result = run_evaluators(_example(), _state(), latency_ms=1.0)

    evaluator_names = {
        evaluator.evaluator_name for evaluator in result.evaluator_results
    }
    assert "helpfulness" in evaluator_names
    assert "category_accuracy" in evaluator_names
