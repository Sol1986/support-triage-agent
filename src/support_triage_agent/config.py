"""Central place to read environment configuration.

Every other module reads settings through these functions rather than calling
`os.getenv` directly, so defaults, validation, and .env loading stay in one spot.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def is_llm_enabled() -> bool:
    """Whether ticket triage should call Gemini, versus falling back to deterministic rules."""
    value = os.getenv("LLM_ENABLED", "false")
    return value.lower().strip() == "true"


def get_gemini_model() -> str:
    """Name of the Gemini model used for classification and drafting."""
    return os.getenv(
        "GEMINI_MODEL",
        "gemini-3.6-flash",
    )


def get_gemini_api_key() -> str:
    """API key for Gemini; raises early if it's missing rather than failing on first call."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")

    return api_key


def is_database_enabled() -> bool:
    """Whether ticket results should be persisted, versus running the API stateless."""
    value = os.getenv("DATABASE_ENABLED", "false")
    return value.lower().strip() == "true"


def get_database_url() -> str:
    """SQLAlchemy connection URL for the tickets database."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing. Add it to the environment.")

    return database_url
