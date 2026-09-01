"""End-to-end smoke tests: ticket -> graph -> deterministic processing ->
evaluation -> revision -> final result, run entirely in deterministic mode
(no live Gemini calls, per `conftest.disable_external_services`).
"""

from support_triage_agent.pipeline import process_ticket


def test_ticket_completes_the_full_pipeline_without_revision() -> None:
    result = process_ticket("I was charged twice and need a refund immediately.")

    assert result["category"] == "billing"
    assert result["priority"] == "high"
    assert result["evaluation_score"] == 10
    assert result["revision_count"] == 1
    # A routine duplicate-charge complaint matches none of the escalation
    # policy's rules — see guardrails/policy.py.
    assert result["requires_human_review"] is False
    assert result["llm_enabled"] is False
    assert result["model_used"] == "deterministic-rules"


def test_ambiguous_ticket_still_reaches_a_final_result() -> None:
    result = process_ticket("Something is wrong with my order, please help.")

    assert result["category"] in {
        "billing",
        "technical",
        "account",
        "shipping",
        "general",
    }
    assert result["priority"] in {"low", "medium", "high"}
    assert result["evaluation_score"] >= 4
    assert isinstance(result["requires_human_review"], bool)
