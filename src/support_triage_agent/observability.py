import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter, Histogram

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


def record_ticket_result(result: Any) -> None:
    """Update business metrics without logging customer ticket text."""

    def read_value(name: str, default: Any) -> Any:
        if isinstance(result, dict):
            return result.get(name, default)

        return getattr(result, name, default)

    category = str(read_value("category", "unknown"))
    priority = str(read_value("priority", "unknown"))
    llm_enabled = str(bool(read_value("llm_enabled", False))).lower()
    revision_count = int(read_value("revision_count", 0))
    requires_human_review = bool(read_value("requires_human_review", False))

    TICKETS_PROCESSED.labels(
        category=category,
        priority=priority,
        llm_enabled=llm_enabled,
    ).inc()

    TICKET_REVISIONS.observe(revision_count)

    if requires_human_review:
        HUMAN_REVIEW_REQUIRED.inc()
