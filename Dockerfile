# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS builder

LABEL org.opencontainers.image.title="Support Ticket Triage Agent"
LABEL org.opencontainers.image.description="LangGraph and FastAPI support-ticket workflow"
LABEL org.opencontainers.image.source="https://github.com/sol-ai-architecture-lab/support-triage-agent"
LABEL org.opencontainers.image.version="0.7.0"


COPY --from=ghcr.io/astral-sh/uv:0.11.32 \
    /uv \
    /uvx \
    /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

RUN uv sync \
    --locked \
    --no-dev \
    --no-install-project

COPY src ./src

RUN uv sync \
    --locked \
    --no-dev \
    --no-editable


FROM python:${PYTHON_VERSION}-slim AS runtime

RUN groupadd --system appgroup \
    && useradd \
        --system \
        --gid appgroup \
        --home-dir /app \
        appuser

WORKDIR /app

COPY --from=builder \
    --chown=appuser:appgroup \
    /app/.venv \
    /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LLM_ENABLED=false
ENV GEMINI_MODEL=gemini-3.6-flash

USER appuser

EXPOSE 8000

HEALTHCHECK \
    --interval=10s \
    --timeout=3s \
    --start-period=10s \
    --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "support_triage_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]