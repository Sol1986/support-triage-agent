"""SQLAlchemy ORM models for persisted ticket data."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from support_triage_agent.database import Base
from support_triage_agent.models import TicketResponse


class TicketRecord(Base):
    """A processed ticket persisted to the "tickets" table, mirroring `TicketState`."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    ticket_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    draft_response: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evaluation_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    evaluation_feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    revision_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    requires_human_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    llm_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# NOTE: duplicates models.StoredTicketResponse/ReadinessResponse, which are what api.py
# actually imports. Kept as-is (unused) to avoid changing behavior outside this doc pass.
class StoredTicketResponse(TicketResponse):
    """Unused duplicate of `models.StoredTicketResponse`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ReadinessResponse(BaseModel):
    """Unused duplicate of `models.ReadinessResponse`."""

    status: str
    database: str
