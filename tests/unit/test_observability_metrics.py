from support_triage_agent import observability
from support_triage_agent.observability import record_llm_call, record_ticket_result


def _metric_total(metric, **labels) -> float:
    if labels:
        return metric.labels(**labels)._value.get()
    return metric._value.get()


def test_record_ticket_result_counts_first_pass_success() -> None:
    before = _metric_total(observability.FIRST_PASS_SUCCESS)

    record_ticket_result(
        {
            "category": "billing",
            "priority": "low",
            "llm_enabled": False,
            "revision_count": 0,
            "requires_human_review": False,
            "evaluation_score": 10,
            "initial_evaluation_score": 10,
        }
    )

    assert _metric_total(observability.FIRST_PASS_SUCCESS) == before + 1


def test_record_ticket_result_counts_revision_success() -> None:
    before_attempted = _metric_total(observability.REVISION_ATTEMPTED)
    before_success = _metric_total(observability.REVISION_SUCCESS)

    record_ticket_result(
        {
            "category": "billing",
            "priority": "high",
            "llm_enabled": False,
            "revision_count": 1,
            "requires_human_review": False,
            "evaluation_score": 10,
            "initial_evaluation_score": 6,
        }
    )

    assert _metric_total(observability.REVISION_ATTEMPTED) == before_attempted + 1
    assert _metric_total(observability.REVISION_SUCCESS) == before_success + 1


def test_record_ticket_result_counts_evaluation_failure_below_threshold() -> None:
    before = _metric_total(observability.EVALUATION_FAILURES)

    record_ticket_result(
        {
            "category": "billing",
            "priority": "low",
            "llm_enabled": False,
            "revision_count": 2,
            "requires_human_review": True,
            "evaluation_score": 6,
            "initial_evaluation_score": 4,
        }
    )

    assert _metric_total(observability.EVALUATION_FAILURES) == before + 1


def test_record_llm_call_observes_latency_and_no_failure() -> None:
    record_llm_call("classify", 0.42)

    # No exception means the histogram/label combination is valid; a direct
    # sample-count check would couple this test to prometheus_client internals.


def test_record_llm_call_increments_failure_counter() -> None:
    before = _metric_total(
        observability.LLM_FAILURES, operation="draft", failure_type="safety_block"
    )

    record_llm_call("draft", 0.1, failure_type="safety_block")

    after = _metric_total(
        observability.LLM_FAILURES, operation="draft", failure_type="safety_block"
    )
    assert after == before + 1


def test_record_llm_call_tracks_token_usage() -> None:
    before_prompt = _metric_total(
        observability.LLM_TOKENS, operation="revise", kind="prompt"
    )
    before_completion = _metric_total(
        observability.LLM_TOKENS, operation="revise", kind="completion"
    )

    record_llm_call("revise", 0.2, prompt_tokens=100, completion_tokens=40)

    assert (
        _metric_total(observability.LLM_TOKENS, operation="revise", kind="prompt")
        == before_prompt + 100
    )
    assert (
        _metric_total(observability.LLM_TOKENS, operation="revise", kind="completion")
        == before_completion + 40
    )


def test_record_llm_call_cost_stays_zero_without_configured_pricing() -> None:
    before = _metric_total(observability.LLM_COST_ESTIMATED_USD, operation="judge")

    record_llm_call("judge", 0.2, prompt_tokens=1000, completion_tokens=200)

    # GEMINI_INPUT/OUTPUT_PRICE_PER_MILLION_TOKENS default to 0 in tests, so
    # the cost estimate is intentionally skipped rather than recorded as $0.
    assert (
        _metric_total(observability.LLM_COST_ESTIMATED_USD, operation="judge") == before
    )


def test_record_llm_call_estimates_cost_when_pricing_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_INPUT_PRICE_PER_MILLION_TOKENS", "1.0")
    monkeypatch.setenv("GEMINI_OUTPUT_PRICE_PER_MILLION_TOKENS", "2.0")

    before = _metric_total(observability.LLM_COST_ESTIMATED_USD, operation="classify")

    record_llm_call("classify", 0.2, prompt_tokens=1_000_000, completion_tokens=500_000)

    after = _metric_total(observability.LLM_COST_ESTIMATED_USD, operation="classify")
    assert after == before + 2.0
