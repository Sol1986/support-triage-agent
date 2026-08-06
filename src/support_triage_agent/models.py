from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class TicketRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ticket_text": (
                        "I was charged twice and need a refund "
                        "immediately."
                    )
                }
            ]
        }
    )

    ticket_text: str = Field(
        min_length=10,
        max_length=5000,
        description="The customer's support request.",
    )


class TicketResponse(BaseModel):
    ticket_text: str
    category: str
    priority: str
    summary: str
    draft_response: str
    evaluation_score: int
    evaluation_feedback: str
    revision_count: int
    requires_human_review: bool