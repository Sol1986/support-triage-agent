"""Aggregates per-example `EvalRunResult`s into the golden-dataset-level metrics
described in docs/EVALS_GUARDRAILS_PLAN.md.

Each metric is `None` when there's no data to compute it from (e.g.
`average_response_quality` when LLM-judge evaluators didn't run), rather than
a misleading 0.0 or 1.0 — callers (the CLI, CI gate) must handle that case
explicitly.
"""

from statistics import mean

from pydantic import BaseModel

from support_triage_agent.evals.models import EvalRunResult

_RESPONSE_QUALITY_DIMENSIONS = {
    "helpfulness",
    "clarity",
    "professionalism",
    "next_step_specificity",
}


class EvalMetrics(BaseModel):
    """The 10 golden-dataset metrics required by docs/EVALS_GUARDRAILS_PLAN.md."""

    example_count: int
    category_accuracy: float | None = None
    priority_accuracy: float | None = None
    high_priority_recall: float | None = None
    human_escalation_accuracy: float | None = None
    response_completeness_rate: float | None = None
    average_response_quality: float | None = None
    hallucination_rate: float | None = None
    first_pass_success_rate: float | None = None
    revision_success_rate: float | None = None
    average_revision_improvement: float | None = None


def _rate_for(results: list[EvalRunResult], evaluator_name: str) -> float | None:
    """Pass rate for one named evaluator, across every run that produced a result for it."""
    passes = [
        evaluator.passed
        for run in results
        for evaluator in run.evaluator_results
        if evaluator.evaluator_name == evaluator_name and evaluator.passed is not None
    ]

    return mean(1.0 if passed else 0.0 for passed in passes) if passes else None


def compute_metrics(results: list[EvalRunResult]) -> EvalMetrics:
    """Aggregate a full golden-dataset run into the 10 headline metrics."""
    response_quality_scores = [
        evaluator.score
        for run in results
        for evaluator in run.evaluator_results
        if evaluator.evaluator_name in _RESPONSE_QUALITY_DIMENSIONS
        and evaluator.score is not None
    ]
    average_response_quality = (
        mean(response_quality_scores) if response_quality_scores else None
    )

    hallucination_detected_rate = _rate_for(results, "hallucination_detection")
    hallucination_rate = (
        1.0 - hallucination_detected_rate
        if hallucination_detected_rate is not None
        else None
    )

    revised_runs = [run for run in results if run.revision_trace.revision_count > 0]
    first_pass_success_rate = (
        mean(1.0 if run.revision_trace.revision_count == 0 else 0.0 for run in results)
        if results
        else None
    )
    revision_success_rate = (
        mean(1.0 if run.revision_trace.improved else 0.0 for run in revised_runs)
        if revised_runs
        else None
    )
    average_revision_improvement = (
        mean(
            run.revision_trace.final_score - run.revision_trace.initial_score
            for run in revised_runs
        )
        if revised_runs
        else None
    )

    return EvalMetrics(
        example_count=len(results),
        category_accuracy=_rate_for(results, "category_accuracy"),
        priority_accuracy=_rate_for(results, "priority_accuracy"),
        high_priority_recall=_rate_for(results, "high_priority_recall"),
        human_escalation_accuracy=_rate_for(results, "human_escalation_accuracy"),
        response_completeness_rate=_rate_for(results, "required_response_elements"),
        average_response_quality=average_response_quality,
        hallucination_rate=hallucination_rate,
        first_pass_success_rate=first_pass_success_rate,
        revision_success_rate=revision_success_rate,
        average_revision_improvement=average_revision_improvement,
    )
