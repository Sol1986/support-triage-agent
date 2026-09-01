"""No test in this file makes a real network call: `Client`/`evaluate` are
always monkeypatched, and `LANGSMITH_TRACING` defaults to false in tests
(see conftest.disable_external_services).
"""

from types import SimpleNamespace

from support_triage_agent.evals import langsmith_adapter
from support_triage_agent.evals.models import GoldenExample


def _example(example_id="TEST-01") -> GoldenExample:
    return GoldenExample.model_validate(
        {
            "id": example_id,
            "ticket_text": "I was charged twice for my subscription.",
            "expected_category": "billing",
            "expected_priority": "high",
            "expected_requires_human_review": False,
            "tags": ["billing"],
        }
    )


def test_get_langsmith_client_returns_none_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    assert langsmith_adapter.get_langsmith_client() is None


def test_get_langsmith_client_returns_none_on_construction_failure(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")

    def raise_error(*args, **kwargs):
        raise RuntimeError("no credentials")

    monkeypatch.setattr(langsmith_adapter, "Client", raise_error)

    assert langsmith_adapter.get_langsmith_client() is None


def test_upload_dataset_no_ops_when_langsmith_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    uploaded = langsmith_adapter.upload_dataset([_example()])

    assert uploaded == 0


class _FakeExample:
    def __init__(self, golden_id: str) -> None:
        self.metadata = {"golden_id": golden_id}


class _FakeLangsmithClient:
    def __init__(self, existing_ids: list[str]) -> None:
        self.existing_ids = existing_ids
        self.created_dataset = False
        self.created_examples_calls = []

    def has_dataset(self, dataset_name: str) -> bool:
        return False

    def create_dataset(self, **kwargs) -> None:
        self.created_dataset = True

    def list_examples(self, dataset_name: str):
        return [_FakeExample(golden_id) for golden_id in self.existing_ids]

    def create_examples(self, **kwargs) -> None:
        self.created_examples_calls.append(kwargs)


def test_upload_dataset_creates_the_dataset_and_uploads_new_examples(
    monkeypatch,
) -> None:
    fake_client = _FakeLangsmithClient(existing_ids=[])
    monkeypatch.setattr(langsmith_adapter, "get_langsmith_client", lambda: fake_client)

    uploaded = langsmith_adapter.upload_dataset([_example("A"), _example("B")])

    assert uploaded == 2
    assert fake_client.created_dataset is True
    assert len(fake_client.created_examples_calls) == 1
    assert len(fake_client.created_examples_calls[0]["inputs"]) == 2


def test_upload_dataset_skips_examples_already_present(monkeypatch) -> None:
    fake_client = _FakeLangsmithClient(existing_ids=["A"])
    monkeypatch.setattr(langsmith_adapter, "get_langsmith_client", lambda: fake_client)

    uploaded = langsmith_adapter.upload_dataset([_example("A"), _example("B")])

    assert uploaded == 1
    assert fake_client.created_examples_calls[0]["metadata"][0]["golden_id"] == "B"


def test_run_experiment_no_ops_when_langsmith_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    assert langsmith_adapter.run_experiment() is None


def test_run_experiment_wires_target_and_evaluators_into_langsmith_evaluate(
    monkeypatch,
) -> None:
    fake_client = object()
    monkeypatch.setattr(langsmith_adapter, "get_langsmith_client", lambda: fake_client)

    captured = {}

    def fake_evaluate(target, *, data, evaluators, experiment_prefix, client):
        captured["target"] = target
        captured["data"] = data
        captured["evaluators"] = evaluators
        captured["experiment_prefix"] = experiment_prefix
        captured["client"] = client
        return "experiment-results"

    monkeypatch.setattr(langsmith_adapter, "langsmith_evaluate", fake_evaluate)

    result = langsmith_adapter.run_experiment(
        dataset_name="my-dataset", experiment_prefix="my-exp"
    )

    assert result == "experiment-results"
    assert captured["data"] == "my-dataset"
    assert captured["experiment_prefix"] == "my-exp"
    assert captured["client"] is fake_client
    assert len(captured["evaluators"]) == 6


def test_adapted_evaluator_scores_a_correct_category_prediction() -> None:
    from support_triage_agent.evals import deterministic

    adapted = langsmith_adapter._adapt_evaluator(deterministic.category_accuracy)

    run = SimpleNamespace(outputs={"category": "billing", "priority": "high"})
    example = SimpleNamespace(
        id="fallback-id",
        metadata={"golden_id": "A"},
        inputs={"ticket_text": "I was charged twice."},
        outputs={
            "expected_category": "billing",
            "expected_priority": "high",
            "expected_requires_human_review": False,
        },
    )

    result = adapted(run, example)

    assert result == {"key": "category_accuracy", "score": 1.0}


def test_adapted_evaluator_skips_when_underlying_evaluator_returns_none() -> None:
    from support_triage_agent.evals import deterministic

    adapted = langsmith_adapter._adapt_evaluator(deterministic.high_priority_recall)

    run = SimpleNamespace(outputs={"category": "billing", "priority": "low"})
    example = SimpleNamespace(
        id="fallback-id",
        metadata={"golden_id": "A"},
        inputs={"ticket_text": "A routine question."},
        outputs={
            "expected_category": "billing",
            "expected_priority": "low",
            "expected_requires_human_review": False,
        },
    )

    result = adapted(run, example)

    assert result == {"key": "high_priority_recall", "score": None}
