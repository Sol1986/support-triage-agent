from typing import TypedDict


class TicketState(TypedDict):
    ticket_text: str
    category: str
    priority: str
    summary: str
    draft_response: str
    evaluation_score: int
    evaluation_feedback: str
    revision_count: int
    requires_human_review: bool