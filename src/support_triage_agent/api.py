from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from support_triage_agent.config import is_database_enabled
from support_triage_agent.database import (
    create_session,
    database_is_ready,
    init_database,
)
from support_triage_agent.db_models import TicketRecord
from support_triage_agent.models import (
    HealthResponse,
    ReadinessResponse,
    StoredTicketResponse,
    TicketRequest,
    TicketResponse,
)
from support_triage_agent.pipeline import process_ticket
from support_triage_agent.repository import (
    get_ticket,
    list_tickets,
    save_ticket,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if is_database_enabled():
        init_database()

    yield


app = FastAPI(
    title="Support Ticket Triage API",
    description=(
        "A LangGraph workflow that classifies support tickets, "
        "assigns priority, drafts responses, evaluates quality, "
        "and stores results."
    ),
    version="0.8.0",
    lifespan=lifespan,
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


# FastAPI will: Open a database session. Pass it to the endpoint. Execute the endpoint. Close the session afterward.
def require_database() -> Generator[Session, None, None]:
    if not is_database_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database persistence is disabled.",
        )

    session = create_session()

    try:
        yield session
    finally:
        session.close()


DatabaseSession = Annotated[
    Session,
    Depends(require_database),
]


# database_is_ready() checks if the database is available and can execute a simple query. If the database is not ready, it raises an HTTP 503 Service Unavailable error. If the database is ready, it returns a ReadinessResponse indicating that the service is ready and the database is connected.
# Is the application ready to handle database work?
@app.get(
    "/ready",
    response_model=ReadinessResponse,
    tags=["System"],
)
def readiness_check() -> ReadinessResponse:
    if not is_database_enabled():
        return ReadinessResponse(
            status="ready",
            database="disabled",
        )

    if not database_is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        )

    return ReadinessResponse(
        status="ready",
        database="connected",
    )


# database session is passed to the endpoint function. The endpoint function uses the session to save a ticket to the database. If the ticket is saved successfully, it returns the stored ticket response. If there is a ValueError during ticket processing, it rolls back the session and raises an HTTP 400 Bad Request error. If there is a SQLAlchemyError during ticket storage, it rolls back the session and raises an HTTP 503 Service Unavailable error.
@app.post(
    "/tickets",
    response_model=StoredTicketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tickets"],
)
def create_stored_ticket(
    request: TicketRequest,
    session: DatabaseSession,
) -> TicketRecord:
    try:
        result = process_ticket(request.ticket_text)
        return save_ticket(session, result)

    except ValueError as error:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except SQLAlchemyError as error:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ticket storage is unavailable.",
        ) from error


# database session is passed to the endpoint function. The endpoint function uses the session to list tickets from the database with pagination. It returns a list of stored ticket responses.
@app.get(
    "/tickets",
    response_model=list[StoredTicketResponse],
    tags=["Tickets"],
)
def read_tickets(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TicketRecord]:
    return list_tickets(
        session=session,
        limit=limit,
        offset=offset,
    )


# database session is passed to the endpoint function. The endpoint function uses the session to retrieve a specific ticket by its ID. If the ticket is found, it returns the stored ticket response. If the ticket is not found, it raises an HTTP 404 Not Found error.
@app.get(
    "/tickets/{ticket_id}",
    response_model=StoredTicketResponse,
    tags=["Tickets"],
)
def read_ticket(
    ticket_id: int,
    session: DatabaseSession,
) -> TicketRecord:
    ticket = get_ticket(session, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return ticket
