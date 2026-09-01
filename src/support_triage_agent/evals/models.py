"""Pydantic models for the offline evaluation harness.

These are eval-only data shapes — separate from `state.TicketState` (the
production graph state) and `models` (the API wire format) — so instrumenting
evaluation runs never has to touch the production request/response contracts.
"""

from typing import Literal

from pydantic import BaseModel, Field

from support_triage_agent.llm import Priority, TicketCategory


class GoldenExample(BaseModel):
    """One curated support ticket with its expected triage outcome."""

    id: str
    ticket_text: str
    expected_category: TicketCategory
    expected_priority: Priority
    expected_requires_human_review: bool
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class EvaluatorResult(BaseModel):
    """Outcome of a single evaluator run against one golden example."""

    evaluator_name: str
    kind: Literal["deterministic", "llm_judge"]
    passed: bool | None = None
    score: float | None = None
    detail: str | None = None


class RevisionTrace(BaseModel):
    """Before/after view of the evaluator-optimizer (revision) loop for one ticket."""

    initial_score: int
    final_score: int
    revision_count: int
    improved: bool


class EvalRunResult(BaseModel):
    """Full result of running one golden example through the pipeline and its evaluators."""

    example_id: str
    actual_category: str
    actual_priority: str
    actual_requires_human_review: bool
    evaluator_results: list[EvaluatorResult]
    revision_trace: RevisionTrace
    latency_ms: float


class QualityJudgment(BaseModel):
    """Structured LLM-as-judge output for a single draft response.

    Mirrors the `ClassificationResult`/`ResponseResult` pattern in `llm.py`:
    passed as Gemini's `response_schema` so judge output is always
    structured, never free-form text.
    """

    helpfulness: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    professionalism: int = Field(ge=1, le=5)
    next_step_specificity: int = Field(ge=1, le=5)
    faithful_to_ticket: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    rationale: str
