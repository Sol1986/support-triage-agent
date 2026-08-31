"""Pydantic schemas for the API's request and response bodies.

These are kept separate from `state.TicketState` (the LangGraph working state)
and `db_models.TicketRecord` (the ORM model) so that the wire format can
evolve independently of the graph's internal state and the storage schema.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Liveness probe payload: confirms the process is up, not that its dependencies are."""

    status: str
    service: str


class TicketRequest(BaseModel):
    """Inbound payload for submitting a support ticket for triage."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"ticket_text": ("I was charged twice and need a refund immediately.")}
            ]
        }
    )

    ticket_text: str = Field(
        min_length=10,
        max_length=5000,
        description="The customer's support request.",
    )


class TicketResponse(BaseModel):
    """Result of running a ticket through the triage graph."""

    ticket_text: str
    category: str
    priority: str
    summary: str
    draft_response: str
    evaluation_score: int
    evaluation_feedback: str
    revision_count: int
    requires_human_review: bool
    llm_enabled: bool
    model_used: str


class StoredTicketResponse(TicketResponse):
    """A `TicketResponse` that has been persisted, with its database identity."""

    # from_attributes lets Pydantic build this directly from a TicketRecord ORM object.
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ReadinessResponse(BaseModel):
    """Readiness probe payload: reports whether dependencies (e.g. the database) are usable."""

    status: str
    database: str
