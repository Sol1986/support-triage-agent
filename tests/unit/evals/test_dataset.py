import pytest

from support_triage_agent.evals.dataset import DEFAULT_DATASET_PATH, load_golden_dataset
from support_triage_agent.evals.models import GoldenExample


def test_load_golden_dataset_returns_validated_examples() -> None:
    examples = load_golden_dataset()

    assert len(examples) > 0
    assert all(isinstance(example, GoldenExample) for example in examples)


def test_load_golden_dataset_skips_blank_lines(tmp_path) -> None:
    dataset_file = tmp_path / "dataset.jsonl"
    dataset_file.write_text(
        '{"id": "A", "ticket_text": "Ticket text here.", "expected_category": "billing", '
        '"expected_priority": "low", "expected_requires_human_review": false}\n'
        "\n"
        '{"id": "B", "ticket_text": "Another ticket.", "expected_category": "general", '
        '"expected_priority": "low", "expected_requires_human_review": false}\n',
        encoding="utf-8",
    )

    examples = load_golden_dataset(dataset_file)

    assert [example.id for example in examples] == ["A", "B"]


def test_load_golden_dataset_fails_loud_on_a_malformed_row(tmp_path) -> None:
    dataset_file = tmp_path / "dataset.jsonl"
    dataset_file.write_text(
        '{"id": "A", "ticket_text": "Ticket text here.", "expected_category": "not_a_category", '
        '"expected_priority": "low", "expected_requires_human_review": false}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid golden example"):
        load_golden_dataset(dataset_file)


def test_default_dataset_path_points_at_the_repo_data_directory() -> None:
    assert DEFAULT_DATASET_PATH.name == "golden_tickets.jsonl"
    assert DEFAULT_DATASET_PATH.exists()
