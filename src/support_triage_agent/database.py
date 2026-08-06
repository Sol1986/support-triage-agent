from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

from support_triage_agent.config import get_database_url


class Base(DeclarativeBase):
    pass


# This file defines the database connection and session management for the support triage agent application. It uses SQLAlchemy to create a database engine, initialize the database schema, check if the database is ready, and create sessions for interacting with the database. The `Base` class serves as the declarative base for defining ORM models.
@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
    )


def init_database() -> None:
    from support_triage_agent import db_models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def database_is_ready() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except Exception:
        return False


def create_session() -> Session:
    return Session(get_engine())
