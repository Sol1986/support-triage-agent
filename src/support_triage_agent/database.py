"""Database engine, schema, and session management.

Keeps SQLAlchemy setup in one place so the API and CLI don't each construct
their own engine/session logic.
"""

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

from support_triage_agent.config import get_database_url


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models (see `db_models.py`)."""

    pass


@lru_cache
def get_engine() -> Engine:
    """Return a process-wide engine; cached so connection pooling is actually shared."""
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
    )


def init_database() -> None:
    """Create any missing tables for models registered on `Base`."""
    # Imported here (not at module load) so db_models registers with Base
    # only when a database is actually configured, and to avoid a circular import.
    from support_triage_agent import db_models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def database_is_ready() -> bool:
    """Check connectivity for the /ready endpoint; returns False on any error."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except Exception:
        return False


def create_session() -> Session:
    """Create a new ORM session; callers are responsible for closing it."""
    return Session(get_engine())
