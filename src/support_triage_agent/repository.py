"""Database access functions for ticket records.

Isolated from `api.py` and the LangGraph nodes so neither has to know about
SQLAlchemy directly.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from support_triage_agent.db_models import TicketRecord
from support_triage_agent.state import TicketState


def save_ticket(
    session: Session,
    result: TicketState,
) -> TicketRecord:
    """Persist a completed triage result and return the row with its assigned id."""
    record = TicketRecord(
        ticket_text=result["ticket_text"],
        category=result["category"],
        priority=result["priority"],
        summary=result["summary"],
        draft_response=result["draft_response"],
        evaluation_score=result["evaluation_score"],
        evaluation_feedback=result["evaluation_feedback"],
        revision_count=result["revision_count"],
        requires_human_review=result["requires_human_review"],
        llm_enabled=result["llm_enabled"],
        model_used=result["model_used"],
    )

    session.add(record)
    session.commit()
    session.refresh(record)

    return record


def list_tickets(
    session: Session,
    limit: int = 20,
    offset: int = 0,
) -> list[TicketRecord]:
    """Return the most recent tickets, newest first, paginated by limit/offset."""
    statement = (
        select(TicketRecord)
        .order_by(TicketRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement))


def get_ticket(
    session: Session,
    ticket_id: int,
) -> TicketRecord | None:
    """Fetch a single ticket by id, or None if it doesn't exist."""
    return session.get(TicketRecord, ticket_id)
