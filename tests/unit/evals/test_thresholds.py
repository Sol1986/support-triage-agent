from support_triage_agent.evals.thresholds import (
    DETERMINISTIC_MODE_THRESHOLDS,
    check_thresholds,
)


def test_passes_when_every_metric_meets_its_threshold() -> None:
    metrics = {name: value for name, value in DETERMINISTIC_MODE_THRESHOLDS.items()}

    assert check_thresholds(metrics) == []


def test_fails_when_a_metric_drops_below_its_threshold() -> None:
    metrics = dict(DETERMINISTIC_MODE_THRESHOLDS)
    metrics["category_accuracy"] = 0.10

    failures = check_thresholds(metrics)

    assert len(failures) == 1
    assert "category_accuracy" in failures[0]


def test_fails_when_a_gated_metric_is_missing() -> None:
    metrics = {name: None for name in DETERMINISTIC_MODE_THRESHOLDS}

    failures = check_thresholds(metrics)

    assert len(failures) == len(DETERMINISTIC_MODE_THRESHOLDS)


def test_ungated_metrics_are_ignored() -> None:
    metrics = dict(DETERMINISTIC_MODE_THRESHOLDS)
    metrics["average_response_quality"] = None
    metrics["first_pass_success_rate"] = 0.0

    assert check_thresholds(metrics) == []
