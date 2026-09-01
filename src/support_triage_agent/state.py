from typing import TypedDict

# Maximum number of times `revise_response` will rewrite a draft before
# `graph.route_after_evaluation` gives up and finishes anyway. Lives here
# (rather than in graph.py, where it's used) so `guardrails.policy` can
# reference the same constant without importing the graph module.
MAX_REVISIONS = 2


class TicketState(TypedDict):
    """Shared state threaded through every node of the LangGraph triage workflow.

    Each node reads the fields it needs and returns a partial dict of updates;
    LangGraph merges those updates back into this state between node calls.
    """

    ticket_text: str
    category: str
    priority: str
    summary: str
    draft_response: str
    evaluation_score: int
    evaluation_feedback: str
    revision_count: int
    requires_human_review: bool
    llm_enabled: bool
    model_used: str

    # Guardrail-layer fields (see guardrails/ and docs/EVALS_GUARDRAILS_PLAN.md).
    guardrail_flags: list[str]
    escalation_reason: str | None
    initial_evaluation_score: int
    schema_validation_failed: bool
