"""Structured logging and Prometheus metrics for the API.

Metric objects are module-level singletons (Prometheus's convention) so every
importer shares the same counters/histograms rather than registering
duplicates.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter, Histogram

from support_triage_agent.config import (
    get_gemini_input_price_per_million_tokens,
    get_gemini_output_price_per_million_tokens,
)

# Set per-request by api.observe_http_request and read by JsonLogFormatter so
# every log line emitted during a request carries its correlation id.
request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)


HTTP_REQUESTS = Counter(
    "support_triage_http_requests_total",
    "Total HTTP requests received by the API.",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "support_triage_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)

TICKETS_PROCESSED = Counter(
    "support_triage_tickets_total",
    "Total support tickets processed.",
    ["category", "priority", "llm_enabled"],
)

TICKET_REVISIONS = Histogram(
    "support_triage_ticket_revisions",
    "Number of response revisions performed for a ticket.",
    buckets=(0, 1, 2, 3, 4, 5),
)

HUMAN_REVIEW_REQUIRED = Counter(
    "support_triage_human_review_total",
    "Total tickets requiring human review.",
)

FIRST_PASS_SUCCESS = Counter(
    "support_triage_first_pass_success_total",
    "Tickets whose first draft passed evaluation without needing a revision.",
)

REVISION_ATTEMPTED = Counter(
    "support_triage_revision_attempted_total",
    "Tickets that required at least one revision.",
)

REVISION_SUCCESS = Counter(
    "support_triage_revision_success_total",
    "Revised tickets whose evaluation score improved over the first draft.",
)

EVALUATION_FAILURES = Counter(
    "support_triage_evaluation_failures_total",
    "Tickets whose final draft still scored below the quality bar (8/10).",
)

# `operation` is always one of "classify", "draft", "revise", "judge" — a
# small fixed set, never per-ticket or per-request data, so it stays a safe,
# low-cardinality Prometheus label.
LLM_LATENCY = Histogram(
    "support_triage_llm_latency_seconds",
    "Gemini call latency in seconds.",
    ["operation"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)

LLM_FAILURES = Counter(
    "support_triage_llm_failures_total",
    "Gemini calls that failed structured-output validation or were safety-blocked.",
    ["operation", "failure_type"],
)

LLM_TOKENS = Counter(
    "support_triage_llm_tokens_total",
    "Gemini token usage, when reported by the API.",
    ["operation", "kind"],
)

LLM_COST_ESTIMATED_USD = Counter(
    "support_triage_llm_cost_estimated_usd_total",
    "Estimated Gemini spend in USD, derived from token usage and a configured "
    "per-token price. Stays at zero unless GEMINI_INPUT/OUTPUT_PRICE_PER_MILLION_TOKENS "
    "are set, since Gemini pricing isn't something this codebase should hardcode.",
    ["operation"],
)


class JsonLogFormatter(logging.Formatter):
    """Format application logs as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }

        optional_fields = (
            "event",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "category",
            "priority",
            "model",
            "revision_count",
            "requires_human_review",
            "error_type",
        )

        for field in optional_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def configure_logging() -> None:
    """Configure application and Uvicorn logs for container output."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True


def _estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float | None:
    """`None` unless both a per-million-token price is configured, so a
    default `$0.00` never gets mistaken for a real cost estimate."""
    input_price = get_gemini_input_price_per_million_tokens()
    output_price = get_gemini_output_price_per_million_tokens()

    if input_price <= 0 and output_price <= 0:
        return None

    return (prompt_tokens / 1_000_000) * input_price + (
        completion_tokens / 1_000_000
    ) * output_price


def record_llm_call(
    operation: str,
    duration_seconds: float,
    *,
    failure_type: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> None:
    """Record latency, failure, and (when available) token usage/cost for one Gemini call.

    Called from `llm.py` and `evals/llm_judge.py` around each `generate_content`
    call — never with raw ticket text or any other high-cardinality value.
    """
    LLM_LATENCY.labels(operation=operation).observe(duration_seconds)

    if failure_type is not None:
        LLM_FAILURES.labels(operation=operation, failure_type=failure_type).inc()

    if prompt_tokens is not None:
        LLM_TOKENS.labels(operation=operation, kind="prompt").inc(prompt_tokens)

    if completion_tokens is not None:
        LLM_TOKENS.labels(operation=operation, kind="completion").inc(completion_tokens)

    if prompt_tokens is not None or completion_tokens is not None:
        cost = _estimate_cost_usd(prompt_tokens or 0, completion_tokens or 0)
        if cost is not None:
            LLM_COST_ESTIMATED_USD.labels(operation=operation).inc(cost)


def record_ticket_result(result: Any) -> None:
    """Update business metrics without logging customer ticket text."""

    def read_value(name: str, default: Any) -> Any:
        """Read a field from `result`, which may be a dict or a state/model object."""
        if isinstance(result, dict):
            return result.get(name, default)

        return getattr(result, name, default)

    category = str(read_value("category", "unknown"))
    priority = str(read_value("priority", "unknown"))
    llm_enabled = str(bool(read_value("llm_enabled", False))).lower()
    revision_count = int(read_value("revision_count", 0))
    requires_human_review = bool(read_value("requires_human_review", False))
    final_score = int(read_value("evaluation_score", 0))
    initial_score = int(read_value("initial_evaluation_score", final_score))

    TICKETS_PROCESSED.labels(
        category=category,
        priority=priority,
        llm_enabled=llm_enabled,
    ).inc()

    TICKET_REVISIONS.observe(revision_count)

    if requires_human_review:
        HUMAN_REVIEW_REQUIRED.inc()

    if revision_count == 0:
        FIRST_PASS_SUCCESS.inc()
    else:
        REVISION_ATTEMPTED.inc()
        if final_score > initial_score:
            REVISION_SUCCESS.inc()

    if final_score < 8:
        EVALUATION_FAILURES.inc()
