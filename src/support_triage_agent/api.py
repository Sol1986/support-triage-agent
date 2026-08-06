from fastapi import FastAPI, HTTPException, status

from support_triage_agent.models import (
    HealthResponse,
    TicketRequest,
    TicketResponse,
)
from support_triage_agent.pipeline import process_ticket

app = FastAPI(
    title="Support Ticket Triage API",
    description=(
        "A LangGraph workflow that classifies support tickets, "
        "assigns priority, drafts responses, and evaluates quality."
    ),
    version="0.3.0",
)


@app.get("/", tags=["System"])
def read_root() -> dict[str, str]:
    return {
        "service": "Support Ticket Triage API",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="support-ticket-triage",
    )


@app.get(
    "/categories",
    tags=["Tickets"],
)
def list_categories() -> dict[str, list[str]]:
    return {
        "categories": [
            "billing",
            "technical",
            "account",
            "shipping",
            "general",
        ]
    }


@app.post(
    "/tickets/analyze",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    tags=["Tickets"],
)
def analyze_ticket(
    request: TicketRequest,
) -> TicketResponse:
    try:
        result = process_ticket(request.ticket_text)
        return TicketResponse(**result)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ticket processing failed.",
        ) from error
