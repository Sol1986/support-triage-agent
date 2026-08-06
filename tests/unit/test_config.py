import pytest

from support_triage_agent.config import get_gemini_api_key


def test_get_gemini_api_key_raises_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is missing"):
        get_gemini_api_key()
