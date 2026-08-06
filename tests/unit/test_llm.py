import pytest

from support_triage_agent.llm import (
    ClassificationResult,
    GeminiTicketService,
    ResponseResult,
    get_llm_service,
)


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeModels:
    def __init__(self, text: str) -> None:
        self._text = text

    def generate_content(self, **kwargs) -> FakeResponse:
        return FakeResponse(self._text)


class FakeGenaiClient:
    def __init__(self, api_key: str, text: str) -> None:
        self.api_key = api_key
        self.models = FakeModels(text)


@pytest.fixture(autouse=True)
def clear_llm_service_cache():
    get_llm_service.cache_clear()
    yield
    get_llm_service.cache_clear()


@pytest.fixture
def gemini_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")


def make_service(monkeypatch, text: str) -> GeminiTicketService:
    monkeypatch.setattr(
        "support_triage_agent.llm.genai.Client",
        lambda api_key: FakeGenaiClient(api_key=api_key, text=text),
    )
    return GeminiTicketService()


def test_classify_ticket_parses_response(monkeypatch, gemini_api_key) -> None:
    service = make_service(monkeypatch, '{"category": "billing"}')

    result = service.classify_ticket("I was charged twice.")

    assert isinstance(result, ClassificationResult)
    assert result.category == "billing"


def test_classify_ticket_raises_on_empty_response(monkeypatch, gemini_api_key) -> None:
    service = make_service(monkeypatch, "")

    with pytest.raises(RuntimeError, match="empty classification"):
        service.classify_ticket("I was charged twice.")


def test_draft_response_parses_response(monkeypatch, gemini_api_key) -> None:
    service = make_service(
        monkeypatch,
        '{"response": "We received your billing request and will follow up soon."}',
    )

    result = service.draft_response(
        ticket_text="I was charged twice.",
        category="billing",
        priority="high",
    )

    assert isinstance(result, ResponseResult)
    assert "billing" in result.response


def test_draft_response_raises_on_empty_response(monkeypatch, gemini_api_key) -> None:
    service = make_service(monkeypatch, "")

    with pytest.raises(RuntimeError, match="empty draft"):
        service.draft_response(
            ticket_text="I was charged twice.",
            category="billing",
            priority="high",
        )


def test_revise_response_parses_response(monkeypatch, gemini_api_key) -> None:
    service = make_service(
        monkeypatch,
        '{"response": "As a next step, keep your reference number handy for follow-up."}',
    )

    result = service.revise_response(
        ticket_text="I was charged twice.",
        category="billing",
        priority="high",
        current_response="Incomplete response",
        feedback="Missing next step and reference number.",
    )

    assert isinstance(result, ResponseResult)
    assert "As a next step" in result.response


def test_revise_response_raises_on_empty_response(monkeypatch, gemini_api_key) -> None:
    service = make_service(monkeypatch, "")

    with pytest.raises(RuntimeError, match="empty revision"):
        service.revise_response(
            ticket_text="I was charged twice.",
            category="billing",
            priority="high",
            current_response="Incomplete response",
            feedback="Missing next step and reference number.",
        )


def test_get_llm_service_returns_gemini_service(monkeypatch, gemini_api_key) -> None:
    monkeypatch.setattr(
        "support_triage_agent.llm.genai.Client",
        lambda api_key: FakeGenaiClient(api_key=api_key, text="{}"),
    )

    service = get_llm_service()

    assert isinstance(service, GeminiTicketService)
