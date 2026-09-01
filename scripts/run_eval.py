"""CLI: run the golden dataset through the evaluation harness and print metrics.

Usage:
    uv run python scripts/run_eval.py [--json] [--check-thresholds]

Runs in whatever mode `LLM_ENABLED` / `LLM_JUDGE_ENABLED` are set to in the
environment. Deterministic mode (the default) needs no API key and is what
the `evals` CI job runs on every PR, with `--check-thresholds` set so a
regression against `evals/thresholds.py`'s documented baseline fails the job.
"""

import argparse
import time

from support_triage_agent.evals.dataset import load_golden_dataset
from support_triage_agent.evals.harness import run_evaluators
from support_triage_agent.evals.metrics import EvalMetrics, compute_metrics
from support_triage_agent.evals.thresholds import check_thresholds
from support_triage_agent.pipeline import process_ticket


def run_golden_dataset() -> EvalMetrics:
    """Run every golden example through the pipeline and aggregate the results."""
    examples = load_golden_dataset()
    run_results = []

    for example in examples:
        start = time.perf_counter()
        actual_state = process_ticket(example.ticket_text)
        latency_ms = (time.perf_counter() - start) * 1000

        run_results.append(run_evaluators(example, actual_state, latency_ms=latency_ms))

    return compute_metrics(run_results)


def _print_table(metrics: EvalMetrics) -> None:
    print(f"Golden dataset: {metrics.example_count} examples\n")

    for field_name, value in metrics.model_dump().items():
        if field_name == "example_count":
            continue

        display_value = "n/a" if value is None else f"{value:.3f}"
        print(f"  {field_name:<28} {display_value}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Print metrics as JSON instead of a table."
    )
    parser.add_argument(
        "--check-thresholds",
        action="store_true",
        help="Exit non-zero if any metric falls below evals/thresholds.py's baseline.",
    )
    args = parser.parse_args()

    metrics = run_golden_dataset()

    if args.json:
        print(metrics.model_dump_json(indent=2))
    else:
        _print_table(metrics)

    if not args.check_thresholds:
        return 0

    failures = check_thresholds(metrics.model_dump())

    if failures:
        print("\nThreshold check FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nThreshold check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
