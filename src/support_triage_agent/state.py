from typing import TypedDict


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
