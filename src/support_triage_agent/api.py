"""FastAPI application exposing the ticket-triage graph over HTTP."""

import logging
from collections.abc import Generator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.base import RequestResponseEndpoint

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
from support_triage_agent.observability import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS,
    configure_logging,
    record_ticket_result,
    request_id_context,
)
from support_triage_agent.pipeline import process_ticket
from support_triage_agent.repository import (
    get_ticket,
    list_tickets,
    save_ticket,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup, if persistence is enabled."""
    if is_database_enabled():
        init_database()

    yield


configure_logging()
logger = logging.getLogger(__name__)


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


@app.middleware("http")
async def observe_http_request(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Tag every request with a correlation id and record Prometheus/log metrics for it."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    context_token = request_id_context.set(request_id)

    method = request.method
    path = request.url.path
    status_code = 500
    started_at = perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as exc:
        logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "method": method,
                "path": path,
                "status_code": 500,
                "error_type": type(exc).__name__,
            },
        )
        raise

    finally:
        duration_seconds = perf_counter() - started_at

        HTTP_REQUESTS.labels(
            method=method,
            path=path,
            status_code=str(status_code),
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            method=method,
            path=path,
        ).observe(duration_seconds)

        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )

        request_id_context.reset(context_token)


@app.get(
    "/metrics",
    include_in_schema=False,
)
def metrics() -> Response:
    """Expose metrics in Prometheus text format for scraping."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/", tags=["System"])
def read_root() -> dict[str, str]:
    """Basic service info and links, mainly for humans poking at the API."""
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
    """Liveness probe: confirms the process is running, independent of its dependencies."""
    return HealthResponse(
        status="healthy",
        service="support-ticket-triage",
    )


@app.get(
    "/categories",
    tags=["Tickets"],
)
def list_categories() -> dict[str, list[str]]:
    """List the fixed set of categories a ticket can be classified into."""
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
    """Run a ticket through the triage graph without persisting the result."""
    try:
        result = process_ticket(request.ticket_text)
        record_ticket_result(result)
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


def require_database() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, closing it after the endpoint runs.

    Raises 503 up front if persistence is disabled, so endpoints that depend
    on this don't need their own database-enabled check.
    """
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


@app.get(
    "/ready",
    response_model=ReadinessResponse,
    tags=["System"],
)
def readiness_check() -> ReadinessResponse:
    """Readiness probe: confirms the database (if enabled) can actually be reached."""
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
    """Run a ticket through the triage graph and persist the result."""
    try:
        result = process_ticket(request.ticket_text)
        record_ticket_result(result)
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
    """List previously stored tickets, most recent first."""
    return list_tickets(
        session=session,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/tickets/{ticket_id}",
    response_model=StoredTicketResponse,
    tags=["Tickets"],
)
def read_ticket(
    ticket_id: int,
    session: DatabaseSession,
) -> TicketRecord:
    """Fetch a single stored ticket by id, or 404 if it doesn't exist."""
    ticket = get_ticket(session, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return ticket
