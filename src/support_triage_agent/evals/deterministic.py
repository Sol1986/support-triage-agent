"""Deterministic evaluators for the golden-dataset harness.

None of these call an LLM — they compare `pipeline.process_ticket()`'s
output against a `GoldenExample`'s expected values, or inspect flags the
graph already computed. This is what keeps the harness cheap to run on
every PR; `evals/llm_judge.py` is the only place in this package that
spends an LLM call, and only when explicitly enabled.
"""

from support_triage_agent.evals.models import EvaluatorResult, GoldenExample
from support_triage_agent.state import TicketState


def category_accuracy(example: GoldenExample, actual: TicketState) -> EvaluatorResult:
    passed = actual["category"] == example.expected_category

    return EvaluatorResult(
        evaluator_name="category_accuracy",
        kind="deterministic",
        passed=passed,
        detail=f"expected={example.expected_category!r} actual={actual['category']!r}",
    )


def priority_accuracy(example: GoldenExample, actual: TicketState) -> EvaluatorResult:
    passed = actual["priority"] == example.expected_priority

    return EvaluatorResult(
        evaluator_name="priority_accuracy",
        kind="deterministic",
        passed=passed,
        detail=f"expected={example.expected_priority!r} actual={actual['priority']!r}",
    )


def high_priority_recall(
    example: GoldenExample, actual: TicketState
) -> EvaluatorResult | None:
    """Only meaningful when a "high" priority was expected.

    Returns `None` (skipped) for every other example; `evals/metrics.py`
    aggregates the non-`None` results into a single recall rate.
    """
    if example.expected_priority != "high":
        return None

    passed = actual["priority"] == "high"

    return EvaluatorResult(
        evaluator_name="high_priority_recall",
        kind="deterministic",
        passed=passed,
        detail=f"actual={actual['priority']!r}",
    )


def schema_compliance(example: GoldenExample, actual: TicketState) -> EvaluatorResult:
    """Passes unless a structured-output validation failure was flagged during the run.

    `schema_validation_failed` is set by the output guardrail; it defaults to
    "compliant" via `.get()` for any state produced before that guardrail
    existed, so this evaluator degrades gracefully rather than raising.
    """
    failed = actual.get("schema_validation_failed", False)

    return EvaluatorResult(
        evaluator_name="schema_compliance",
        kind="deterministic",
        passed=not failed,
    )


def required_response_elements(
    example: GoldenExample, actual: TicketState
) -> EvaluatorResult:
    """Reuses `nodes.evaluate_response`'s own required-elements check rather than
    re-implementing its substring logic: a score of 10 means every check passed.
    """
    passed = actual["evaluation_score"] == 10

    return EvaluatorResult(
        evaluator_name="required_response_elements",
        kind="deterministic",
        passed=passed,
        detail=actual["evaluation_feedback"],
    )


def human_escalation_accuracy(
    example: GoldenExample, actual: TicketState
) -> EvaluatorResult:
    passed = actual["requires_human_review"] == example.expected_requires_human_review

    return EvaluatorResult(
        evaluator_name="human_escalation_accuracy",
        kind="deterministic",
        passed=passed,
        detail=(
            f"expected={example.expected_requires_human_review!r} "
            f"actual={actual['requires_human_review']!r}"
        ),
    )
