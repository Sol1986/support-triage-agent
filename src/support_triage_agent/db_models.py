from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from support_triage_agent.database import Base
from support_triage_agent.models import TicketResponse


# This file defines the database models for the support triage agent application. It uses SQLAlchemy's ORM to map Python classes to database tables. The `TicketRecord` class represents a ticket in the system, with various attributes such as ticket text, category, priority, summary, draft response, evaluation score and feedback, revision count, human review requirement, LLM enablement, model used, and creation timestamp. Each attribute is mapped to a corresponding column in the "tickets" table in the database.
# This maps a Python class to a PostgreSQL table
# The `TicketRecord` class represents a ticket in the system, with various attributes such as ticket text, category, priority, summary, draft response, evaluation score and feedback, revision count, human review requirement, LLM enablement, model used, and creation timestamp. Each attribute is mapped to a corresponding column in the "tickets" table in the database.
class TicketRecord(Base):
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


# from_attributes=True allows Pydantic to create an API response from a SQLAlchemy object.
class StoredTicketResponse(TicketResponse):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ReadinessResponse(BaseModel):
    status: str
    database: str
