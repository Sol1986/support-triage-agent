"""Documented CI regression thresholds for the golden-dataset evaluation.

Deterministic mode (`LLM_ENABLED=false`, the CI-safe default) is fully
deterministic — the same `data/golden_tickets.jsonl` always drives the same
`classify_ticket` / `assign_priority` / `guardrails.policy` logic to the same
output. So these thresholds are set at the exact baseline measured against
that dataset (see docs/EVALS_GUARDRAILS_PLAN.md, Phase 1/2, updated
2026-09-01 after widening `HIGH_PRIORITY_KEYWORDS` to cover outage-style
language), not an arbitrary or invented number — not a relative-regression
band, because there's no run-to-run noise to band against. A metric dropping
below its threshold means something in that deterministic path regressed. An
intentional improvement to that logic should raise the corresponding
threshold in the same PR, not be silently tolerated by a stale gate.

`average_response_quality` and `hallucination_rate` have no threshold here —
they're only populated when `LLM_JUDGE_ENABLED=true` (Phase 3), which the
default CI job never sets (see docs/EVALS_GUARDRAILS_PLAN.md §12 on
judge-eval cost). `first_pass_success_rate` and `average_revision_improvement`
are informational, not gated: today's deterministic templates always need
exactly one revision to hit the required-elements bar, so "0% first-pass"
is expected behavior, not a regression signal.
"""

# Baseline measured 2026-09-01 against LLM_ENABLED=false, LLM_JUDGE_ENABLED=false,
# data/golden_tickets.jsonl (49 examples), after widening HIGH_PRIORITY_KEYWORDS
# to cover outage-style language ("completely down", "can't work", "outage", ...).
# Rounded down slightly from the measured value as a floating-point safety
# margin, not a tolerance band.
DETERMINISTIC_MODE_THRESHOLDS: dict[str, float] = {
    "category_accuracy": 0.59,
    "priority_accuracy": 0.46,
    "high_priority_recall": 0.43,
    "human_escalation_accuracy": 0.85,
    "response_completeness_rate": 1.00,
    "revision_success_rate": 1.00,
}


def check_thresholds(metrics_dict: dict[str, float | int | None]) -> list[str]:
    """Compare `metrics_dict` (e.g. `EvalMetrics.model_dump()`) against
    `DETERMINISTIC_MODE_THRESHOLDS`.

    Returns one human-readable failure message per metric that's missing or
    below its threshold; an empty list means every gated metric passed.
    """
    failures = []

    for metric_name, minimum in DETERMINISTIC_MODE_THRESHOLDS.items():
        value = metrics_dict.get(metric_name)

        if value is None:
            failures.append(f"{metric_name}: no data (expected >= {minimum:.3f})")
            continue

        if value < minimum:
            failures.append(
                f"{metric_name}: {value:.3f} is below threshold {minimum:.3f}"
            )

    return failures
