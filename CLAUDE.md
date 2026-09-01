# CLAUDE.md — Project Guidelines

## Build & Test Commands 
- Run fast unit tests: `uv run pytest tests/unit/` 
- Run full integration suite: `uv run pytest tests/integration/` 
- Check styling/linting: `uv run ruff check .` 
- Fix styling & format automatically: `uv run ruff check . --fix && uv run ruff format .`

## Technical Guardrails
- **No Boilerplate:** Write production-grade, defensive code optimized for efficiency and edge cases.
- **Data Integrity:** All multi-step database operations must use explicit ACID transactions.
- **Financial Precision:** Never use standard floats for money. Use the `decimal` module or integer cents.
- **Security:** Do not hardcode configurations or secrets. Load everything via environment variables.
- **Error Handling:** Use a centralized global error-handling wrapper to return structured JSON responses.

## Best Practice when writing code
- Include meaningful Docstrings to explain why a function exists and what it does.
- Include type hinting on all function
- Include some comments to give clarity where it matter in the code. Not on every line of code, but only areas that might improve clarity.

### Here is example:
```python
def event_source(filepath: str) -> Generator[Dict, None, None]:
    """
    Simulate a stream of order events from a file.
    In production, this would consume from Kafka or a message queue.
    """
    with open(filepath, "r") as f:
        for line in f:
            event = json.loads(line.strip())
            yield event
            time.sleep(0.01)  # simulate arrival delay between events
```

## Rules

- Dependencies are added in `pyproject.toml`.
- Use uv for dependency management