from fastapi.testclient import TestClient

from support_triage_agent.api import app

client = TestClient(app)


def test_health_response_contains_request_id() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_existing_request_id_is_preserved() -> None:
    response = client.get(
        "/health",
        headers={"X-Request-ID": "test-request-123"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-123"


def test_metrics_endpoint_exposes_application_metrics() -> None:
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "support_triage_http_requests_total" in response.text
    assert "support_triage_http_request_duration_seconds" in response.text
