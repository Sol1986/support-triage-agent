"""Central dispatch for running every applicable evaluator against one golden example."""

from collections.abc import Callable

from support_triage_agent.config import is_llm_judge_enabled
from support_triage_agent.evals import deterministic
from support_triage_agent.evals.models import (
    EvalRunResult,
    EvaluatorResult,
    GoldenExample,
    RevisionTrace,
)
from support_triage_agent.state import TicketState

DeterministicEvaluator = Callable[[GoldenExample, TicketState], EvaluatorResult | None]

DETERMINISTIC_EVALUATORS: list[DeterministicEvaluator] = [
    deterministic.category_accuracy,
    deterministic.priority_accuracy,
    deterministic.high_priority_recall,
    deterministic.schema_compliance,
    deterministic.required_response_elements,
    deterministic.human_escalation_accuracy,
]


def _build_revision_trace(actual: TicketState) -> RevisionTrace:
    """`initial_evaluation_score` is written once by `evaluate_response` on the
    first pass; fall back to the final score for any state produced before
    that field existed, which reports "no revision improvement data" rather
    than raising.
    """
    initial_score = actual.get("initial_evaluation_score", actual["evaluation_score"])
    final_score = actual["evaluation_score"]

    return RevisionTrace(
        initial_score=initial_score,
        final_score=final_score,
        revision_count=actual["revision_count"],
        improved=final_score > initial_score,
    )


def run_evaluators(
    example: GoldenExample,
    actual: TicketState,
    *,
    latency_ms: float,
) -> EvalRunResult:
    """Run every applicable evaluator for one golden example against its actual result.

    Deterministic evaluators always run. LLM-judge evaluators only run when
    `config.is_llm_judge_enabled()` is true, so CI/unit-test runs never spend
    an LLM call unless explicitly opted in — this is what "don't call an LLM
    when a deterministic evaluator can reliably evaluate the result" means in
    practice.
    """
    results: list[EvaluatorResult] = []

    for evaluator in DETERMINISTIC_EVALUATORS:
        result = evaluator(example, actual)
        if result is not None:
            results.append(result)

    if is_llm_judge_enabled():
        # Imported lazily so importing this module never requires a Gemini client.
        from support_triage_agent.evals import llm_judge

        results.extend(llm_judge.run_judge_evaluators(example, actual))

    return EvalRunResult(
        example_id=example.id,
        actual_category=actual["category"],
        actual_priority=actual["priority"],
        actual_requires_human_review=actual["requires_human_review"],
        evaluator_results=results,
        revision_trace=_build_revision_trace(actual),
        latency_ms=latency_ms,
    )
