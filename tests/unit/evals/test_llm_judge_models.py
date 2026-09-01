"""Tests for the judge output schema and evaluator decomposition — no live
Gemini calls: `llm_judge._judge` is monkeypatched throughout.
"""

import pytest
from pydantic import ValidationError

from support_triage_agent.evals import llm_judge
from support_triage_agent.evals.models import GoldenExample, QualityJudgment


def _example() -> GoldenExample:
    return GoldenExample.model_validate(
        {
            "id": "TEST-01",
            "ticket_text": "I was charged twice for my subscription.",
            "expected_category": "billing",
            "expected_priority": "high",
            "expected_requires_human_review": False,
            "tags": ["billing"],
        }
    )


def test_quality_judgment_requires_scores_within_range() -> None:
    with pytest.raises(ValidationError):
        QualityJudgment(
            helpfulness=6,
            clarity=3,
            professionalism=3,
            next_step_specificity=3,
            faithful_to_ticket=True,
            unsupported_claims=[],
            rationale="ok",
        )


def test_quality_judgment_defaults_unsupported_claims_to_empty_list() -> None:
    judgment = QualityJudgment(
        helpfulness=5,
        clarity=5,
        professionalism=5,
        next_step_specificity=5,
        faithful_to_ticket=True,
        rationale="Great response.",
    )

    assert judgment.unsupported_claims == []


def test_run_judge_evaluators_decomposes_into_six_named_results(monkeypatch) -> None:
    judgment = QualityJudgment(
        helpfulness=4,
        clarity=5,
        professionalism=5,
        next_step_specificity=3,
        faithful_to_ticket=True,
        unsupported_claims=[],
        rationale="Solid response, minor vagueness on next step.",
    )
    monkeypatch.setattr(
        llm_judge, "_judge", lambda ticket_text, draft_response: judgment
    )

    actual = {"draft_response": "We received your request."}
    results = llm_judge.run_judge_evaluators(_example(), actual)

    result_by_name = {result.evaluator_name: result for result in results}
    assert set(result_by_name) == {
        "helpfulness",
        "clarity",
        "professionalism",
        "next_step_specificity",
        "faithfulness_to_ticket",
        "hallucination_detection",
    }
    assert result_by_name["helpfulness"].score == 4
    assert result_by_name["faithfulness_to_ticket"].passed is True
    assert result_by_name["hallucination_detection"].passed is True
    assert all(result.kind == "llm_judge" for result in results)


def test_run_judge_evaluators_flags_hallucinations_as_failed(monkeypatch) -> None:
    judgment = QualityJudgment(
        helpfulness=3,
        clarity=3,
        professionalism=4,
        next_step_specificity=2,
        faithful_to_ticket=False,
        unsupported_claims=[
            "Promised a refund within 24 hours, not stated in the ticket."
        ],
        rationale="Response invents a timeline the ticket never mentioned.",
    )
    monkeypatch.setattr(
        llm_judge, "_judge", lambda ticket_text, draft_response: judgment
    )

    results = llm_judge.run_judge_evaluators(_example(), {"draft_response": "..."})
    result_by_name = {result.evaluator_name: result for result in results}

    assert result_by_name["hallucination_detection"].passed is False
    assert result_by_name["faithfulness_to_ticket"].passed is False
