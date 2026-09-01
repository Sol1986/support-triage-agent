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


def is_llm_judge_enabled() -> bool:
    """Whether the eval harness should run its Gemini-backed judge evaluators.

    Off by default so CI/unit-test runs of the harness never spend an LLM
    call unless explicitly opted in.
    """
    value = os.getenv("LLM_JUDGE_ENABLED", "false")
    return value.lower().strip() == "true"


def get_gemini_input_price_per_million_tokens() -> float:
    """USD per 1M input tokens, used only to derive the estimated-cost metric.

    Defaults to 0 (estimate disabled) since Gemini pricing changes over time
    and shouldn't be hardcoded; set both this and the output price to enable
    `support_triage_llm_cost_estimated_usd_total`.
    """
    return float(os.getenv("GEMINI_INPUT_PRICE_PER_MILLION_TOKENS", "0"))


def get_gemini_output_price_per_million_tokens() -> float:
    """USD per 1M output tokens, used only to derive the estimated-cost metric."""
    return float(os.getenv("GEMINI_OUTPUT_PRICE_PER_MILLION_TOKENS", "0"))


def is_langsmith_enabled() -> bool:
    """Whether LangSmith integrations (tracing, dataset upload, experiments) are active.

    The LangSmith SDK reads `LANGSMITH_TRACING`/`LANGSMITH_API_KEY`/
    `LANGSMITH_PROJECT` itself for auto-instrumentation; this is the one
    canonical check our own code (e.g. `evals/langsmith_adapter.py`) uses
    before touching the SDK at all.
    """
    value = os.getenv("LANGSMITH_TRACING", "false")
    return value.lower().strip() == "true"
