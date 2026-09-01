"""Optional, feature-flagged LangSmith integration: dataset upload and
experiment runs.

Every function here checks `get_langsmith_client()` first and no-ops when it
returns `None` (LangSmith not enabled, or the client failed to construct),
so the eval harness and the production pipeline behave identically whether
or not LangSmith is configured — this is what "never tightly coupled to
LangSmith" means in practice. Production tracing itself (`@traceable` in
`llm.py` and `evals/llm_judge.py`) is unaffected either way; it's
auto-instrumented by the SDK reading `LANGSMITH_TRACING` directly.
"""

import logging
from collections.abc import Callable

from langsmith import Client
from langsmith import evaluate as langsmith_evaluate

from support_triage_agent.config import is_langsmith_enabled
from support_triage_agent.evals.harness import DETERMINISTIC_EVALUATORS
from support_triage_agent.evals.models import EvaluatorResult, GoldenExample
from support_triage_agent.pipeline import process_ticket

logger = logging.getLogger(__name__)

DEFAULT_DATASET_NAME = "support-triage-golden-tickets"


def get_langsmith_client() -> Client | None:
    """Return a LangSmith `Client`, or `None` if tracing isn't enabled or the
    client fails to construct (e.g. missing/invalid credentials)."""
    if not is_langsmith_enabled():
        return None

    try:
        return Client()
    except Exception:
        logger.warning(
            "Failed to construct a LangSmith client; skipping LangSmith integration.",
            exc_info=True,
        )
        return None


def upload_dataset(
    examples: list[GoldenExample],
    dataset_name: str = DEFAULT_DATASET_NAME,
) -> int:
    """Idempotently upsert `examples` into a named LangSmith dataset.

    Only examples not already present (matched by `GoldenExample.id`, stored
    in each LangSmith example's metadata) are uploaded. Returns the number of
    examples uploaded; `0` if LangSmith isn't configured.
    """
    client = get_langsmith_client()
    if client is None:
        return 0

    if not client.has_dataset(dataset_name=dataset_name):
        client.create_dataset(
            dataset_name=dataset_name,
            description="Support-triage golden ticket dataset (see data/golden_tickets.jsonl).",
        )

    existing_ids = {
        existing.metadata.get("golden_id")
        for existing in client.list_examples(dataset_name=dataset_name)
        if existing.metadata
    }
    new_examples = [example for example in examples if example.id not in existing_ids]

    if not new_examples:
        return 0

    client.create_examples(
        inputs=[{"ticket_text": example.ticket_text} for example in new_examples],
        outputs=[
            {
                "expected_category": example.expected_category,
                "expected_priority": example.expected_priority,
                "expected_requires_human_review": example.expected_requires_human_review,
            }
            for example in new_examples
        ],
        metadata=[
            {"golden_id": example.id, "tags": example.tags} for example in new_examples
        ],
        dataset_name=dataset_name,
    )

    return len(new_examples)


def _target(inputs: dict) -> dict:
    """LangSmith experiment run function: process one ticket and return
    everything the wrapped deterministic evaluators need."""
    result = process_ticket(inputs["ticket_text"])

    return {
        "category": result["category"],
        "priority": result["priority"],
        "requires_human_review": result["requires_human_review"],
        "evaluation_score": result["evaluation_score"],
        "evaluation_feedback": result["evaluation_feedback"],
        "draft_response": result["draft_response"],
        "schema_validation_failed": result.get("schema_validation_failed", False),
    }


def _adapt_evaluator(
    evaluator_fn: Callable[[GoldenExample, dict], EvaluatorResult | None],
):
    """Wrap one of `evals/deterministic.py`'s evaluator functions into the
    `(run, example) -> dict` shape LangSmith's `evaluate()` expects — so the
    exact same evaluator logic powers both local CI gating and LangSmith
    experiments, never two parallel implementations."""

    def _evaluate_run(run, example) -> dict:
        golden = GoldenExample(
            id=str(example.metadata.get("golden_id", example.id)),
            ticket_text=example.inputs["ticket_text"],
            expected_category=example.outputs["expected_category"],
            expected_priority=example.outputs["expected_priority"],
            expected_requires_human_review=example.outputs[
                "expected_requires_human_review"
            ],
        )
        actual = dict(run.outputs or {})

        result = evaluator_fn(golden, actual)
        if result is None:
            return {"key": evaluator_fn.__name__, "score": None}

        return {"key": result.evaluator_name, "score": 1.0 if result.passed else 0.0}

    return _evaluate_run


def run_experiment(
    dataset_name: str = DEFAULT_DATASET_NAME,
    experiment_prefix: str = "support-triage",
):
    """Run every deterministic evaluator as a LangSmith experiment against
    `dataset_name`, for comparing prompt/model versions over time.

    No-ops (returns `None`) if LangSmith isn't configured.
    """
    client = get_langsmith_client()
    if client is None:
        return None

    evaluators = [
        _adapt_evaluator(evaluator_fn) for evaluator_fn in DETERMINISTIC_EVALUATORS
    ]

    return langsmith_evaluate(
        _target,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        client=client,
    )
