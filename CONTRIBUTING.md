# Contributing

## Development workflow

1. Update local `main`.
2. Create a focused feature branch.
3. Make one logically related change.
4. Run the complete test suite.
5. Commit with a clear message.
6. Push the feature branch.
7. Open a pull request into `main`.
8. Review the changed files and test evidence.
9. Merge only when validation succeeds.
10. Delete the merged feature branch.

## Local setup

```powershell
uv sync
```

Create `.env` from `.env.example` and add your own API key.

Never commit `.env` or API credentials.

## Run the application

Deterministic mode:

```text
LLM_ENABLED=false
```

Gemini mode:

```text
LLM_ENABLED=true
```

Start the API:

```powershell
uv run fastapi dev src/support_triage_agent/api.py
```

## Run tests

```powershell
uv run pytest -v
```

Run coverage:

```powershell
uv run pytest --cov=support_triage_agent --cov-report=term-missing
```

## Branch naming

Use focused branch names:

```text
feature/add-database
fix/invalid-ticket-response
test/add-timeout-tests
docs/update-architecture
chore/update-dependencies
```

## Commit messages

Use an action-oriented description:

```text
add Gemini structured classification
fix billing escalation rule
test API provider failure
document local development workflow
```

## Pull requests

Each pull request should:

- Solve one focused problem
- Explain the business or technical reason
- Include validation evidence
- Avoid unrelated formatting changes
- Contain no credentials or private configuration