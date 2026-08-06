import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from support_triage_agent.api import app, require_database
from support_triage_agent.database import Base


# This file contains tests for the database API of the support triage agent application. It uses pytest fixtures to set up an in-memory SQLite database for testing purposes. The `database_client` fixture creates a test client that interacts with the FastAPI application, allowing tests to send requests to the API endpoints. The tests verify that tickets can be stored, retrieved, and listed correctly, and that appropriate error responses are returned when expected.
# SQLite is being used only as a fast isolated database for these API contract tests. The Compose integration test will verify actual PostgreSQL.
@pytest.fixture
def database_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    def override_database():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[require_database] = override_database

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_store_and_retrieve_ticket(database_client):
    create_response = database_client.post(
        "/tickets",
        json={"ticket_text": ("I was charged twice and need help immediately.")},
    )

    assert create_response.status_code == 201

    created_ticket = create_response.json()

    assert created_ticket["id"] == 1
    assert created_ticket["category"] == "billing"

    read_response = database_client.get("/tickets/1")

    assert read_response.status_code == 200
    assert read_response.json()["id"] == 1


def test_list_stored_tickets(database_client):
    database_client.post(
        "/tickets",
        json={"ticket_text": ("My package has a delivery problem.")},
    )

    response = database_client.get("/tickets")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_missing_ticket_returns_404(database_client):
    response = database_client.get("/tickets/999")

    assert response.status_code == 404


def test_database_disabled_returns_503():
    with TestClient(app) as client:
        response = client.post(
            "/tickets",
            json={"ticket_text": ("This is a valid support request.")},
        )

    assert response.status_code == 503
