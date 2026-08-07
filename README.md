[![CI](https://github.com/sol-ai-architecture-lab/support-triage-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/sol1986/support-triage-agent/actions/workflows/ci.yml)

# Support Ticket Triage Agent

A support-ticket triage service built as a **LangGraph** workflow behind a **FastAPI** API. It classifies incoming tickets, assigns a priority, drafts a customer-facing response, evaluates that response against quality checks, and automatically revises it if it falls short — with results optionally persisted to PostgreSQL and exposed as Prometheus metrics.

It runs in two modes: fast, free, deterministic keyword rules, or a **Google Gemini**-backed LLM mode for classification and response drafting — toggled with a single environment variable, no code changes.

## How it works

The core is a `LangGraph` state machine ([graph.py](src/support_triage_agent/graph.py)):

```
validate_ticket → classify_ticket → assign_priority → create_summary → draft_response
                                                                             │
                                                                             ▼
                                                                    evaluate_response
                                                                       │        │
                                                          score ≥ 8 or │        │ score < 8
                                                          2 revisions  │        │
                                                                       ▼        ▼
                                                                    finish   revise_response
                                                                                │
                                                                                └──► back to evaluate_response
```

- **Deterministic mode** (default): category and priority come from keyword matching; the response is templated. Zero external dependencies, fully unit-testable, no cost.
- **LLM mode** (`LLM_ENABLED=true`): classification and response drafting/revision are delegated to Gemini via structured-output (Pydantic-schema-constrained) calls, so responses stay type-safe even when the model is generating them.

An automated evaluation node scores each draft against required elements (does it name the category, explain next steps, provide a reference number) and routes back for revision — up to twice — before finishing, so low-quality drafts don't reach the customer unrevised.

## API

| Method | Path                | Purpose                                                   |
| ------ | ------------------- | ---------------------------------------------------------- |
| GET    | `/`                 | Service info                                                |
| GET    | `/health`           | Liveness check                                               |
| GET    | `/ready`             | Readiness check (verifies DB connectivity when enabled)      |
| GET    | `/categories`        | Supported ticket categories                                  |
| POST   | `/tickets/analyze`   | Run the workflow, return the result (no persistence)         |
| POST   | `/tickets`           | Run the workflow and persist the result                      |
| GET    | `/tickets`           | List stored tickets (paginated)                              |
| GET    | `/tickets/{id}`      | Fetch a single stored ticket                                 |
| GET    | `/metrics`           | Prometheus metrics                                            |

Interactive docs are available at `/docs` once the app is running.

## Tech stack

- **Workflow orchestration:** LangGraph
- **LLM:** Google Gemini (`google-genai`), structured output via Pydantic schemas
- **API:** FastAPI
- **Persistence:** PostgreSQL via SQLAlchemy (optional, feature-flagged)
- **Observability:** structured JSON logging, Prometheus metrics, Grafana dashboards
- **Testing:** pytest, pytest-cov (85%+ coverage, enforced in CI)
- **Packaging/tooling:** uv, Ruff (formatting + linting)
- **Infrastructure:** Docker (multi-stage build), Docker Compose, Terraform (Azure Container Apps, Azure Database for PostgreSQL, Azure Container Registry)

## Running locally

**With uv, deterministic mode only:**

```bash
uv sync
uv run python -m support_triage_agent
```

**Full stack (API + PostgreSQL) with Docker Compose:**

```bash
cp .env.example .env   # fill in a database password, and a Gemini key if using LLM mode
docker compose up --build
```

The API is then available at `http://localhost:8000`.

**Monitoring stack (Prometheus + Grafana):**

```bash
docker compose -f monitoring/compose.yaml up
```

## Testing & CI

```bash
uv run pytest --cov=support_triage_agent --cov-report=term-missing --cov-fail-under=80
```

GitHub Actions runs on every PR and push to `main`:
- Ruff formatting and linting
- Full test suite with an enforced 80% coverage gate
- A Docker build + container smoke test against `/health`
- A full Docker Compose integration test against a real PostgreSQL instance (create a ticket, retrieve it)

## Deployment

Provisioned with Terraform ([infrastructure/terraform/](infrastructure/terraform/)) onto Azure Container Apps, with Azure Database for PostgreSQL Flexible Server on a private virtual network, Azure Container Registry, and a user-assigned managed identity for image pulls. See [docs/azure-deployment.md](docs/azure-deployment.md) for the full architecture and current limitations.

## Project layout

```
src/support_triage_agent/
├── api.py             # FastAPI routes, middleware, request lifecycle
├── graph.py            # LangGraph state machine definition
├── nodes.py             # Workflow node implementations (deterministic path)
├── llm.py                # Gemini-backed classification/drafting/revision
├── pipeline.py             # Builds initial state, invokes the graph
├── state.py                 # TicketState TypedDict
├── models.py                 # Pydantic request/response models
├── db_models.py                # SQLAlchemy ORM models
├── database.py                  # Engine/session management
├── repository.py                 # Data-access layer
├── observability.py               # Logging config, Prometheus metrics
└── config.py                       # Environment-driven configuration
```
