from fastapi.testclient import TestClient

from support_triage_agent.api import app

client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Support Ticket Triage API",
        "documentation": "/docs",
        "health": "/health",
    }


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "support-ticket-triage",
    }


def test_categories_endpoint() -> None:
    response = client.get("/categories")

    assert response.status_code == 200
    assert "billing" in response.json()["categories"]
    assert "shipping" in response.json()["categories"]


def test_analyze_ticket_endpoint() -> None:
    response = client.post(
        "/tickets/analyze",
        json={"ticket_text": ("I was charged twice and need a refund immediately.")},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["category"] == "billing"
    assert body["priority"] == "high"
    assert body["evaluation_score"] == 10
    assert body["revision_count"] == 1
    assert body["requires_human_review"] is True


def test_short_ticket_returns_422() -> None:
    response = client.post(
        "/tickets/analyze",
        json={"ticket_text": "Help"},
    )

    assert response.status_code == 422


def test_missing_ticket_text_returns_422() -> None:
    response = client.post(
        "/tickets/analyze",
        json={},
    )

    assert response.status_code == 422


def test_analyze_ticket_whitespace_only_returns_400() -> None:
    # Passes Pydantic's min_length=10 (raw chars) but the internal
    # validate_ticket strips whitespace first, leaving under 10 chars.
    response = client.post(
        "/tickets/analyze",
        json={"ticket_text": "    abc    "},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Ticket must contain at least 10 characters."}


def test_unknown_endpoint_returns_404() -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404


def test_internal_failure_returns_500(
    monkeypatch,
) -> None:
    def simulate_failure(ticket_text: str):
        raise RuntimeError("Simulated graph failure")

    monkeypatch.setattr(
        "support_triage_agent.api.process_ticket",
        simulate_failure,
    )

    response = client.post(
        "/tickets/analyze",
        json={"ticket_text": ("This is a sufficiently long support ticket.")},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Ticket processing failed."}
