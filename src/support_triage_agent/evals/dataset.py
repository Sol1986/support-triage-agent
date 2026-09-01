"""Loads and validates the golden ticket dataset used by the evaluation harness."""

import json
from pathlib import Path

from support_triage_agent.evals.models import GoldenExample

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "golden_tickets.jsonl"
)


def load_golden_dataset(path: Path = DEFAULT_DATASET_PATH) -> list[GoldenExample]:
    """Load and validate every line of the golden dataset.

    Fails loud (raises) on the first malformed row instead of skipping it —
    dataset integrity is itself something CI should catch.
    """
    examples: list[GoldenExample] = []

    with path.open(encoding="utf-8") as dataset_file:
        for line_number, raw_line in enumerate(dataset_file, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
                examples.append(GoldenExample.model_validate(row))
            except Exception as exc:
                raise ValueError(
                    f"Invalid golden example on {path.name}:{line_number}: {exc}"
                ) from exc

    return examples
