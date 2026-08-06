from functools import lru_cache
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from support_triage_agent.config import (
    get_gemini_api_key,
    get_gemini_model,
)

TicketCategory = Literal[
    "billing",
    "technical",
    "account",
    "shipping",
    "general",
]


class ClassificationResult(BaseModel):
    category: TicketCategory = Field(
        description="The best category for the support ticket."
    )


class ResponseResult(BaseModel):
    response: str = Field(
        min_length=20,
        description="The customer-facing support response.",
    )


class GeminiTicketService:
    def __init__(self) -> None:
        self.model = get_gemini_model()
        self.client = genai.Client(api_key=get_gemini_api_key())

    def classify_ticket(
        self,
        ticket_text: str,
    ) -> ClassificationResult:
        prompt = f"""
Classify the following customer support ticket.

Allowed categories:
- billing: charges, refunds, payments, and invoices
- technical: errors, crashes, login failures, and software problems
- account: profiles, subscriptions, cancellations, and account changes
- shipping: packages, shipments, delivery, and arrival problems
- general: requests that do not fit another category

Return the single best category.

Ticket:
{ticket_text}
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=ClassificationResult,
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty classification.")

        return ClassificationResult.model_validate_json(response.text)

    def draft_response(
        self,
        ticket_text: str,
        category: str,
        priority: str,
    ) -> ResponseResult:
        prompt = f"""
Write a concise customer-support response.

Ticket:
{ticket_text}

Category:
{category}

Priority:
{priority}

Requirements:
- Acknowledge the customer's issue.
- State the assigned priority.
- Do not claim that a refund or resolution is guaranteed.
- Explain that a support specialist will review the request.
- Keep the response under 100 words.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=ResponseResult,
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty draft.")

        return ResponseResult.model_validate_json(response.text)

    def revise_response(
        self,
        ticket_text: str,
        category: str,
        priority: str,
        current_response: str,
        feedback: str,
    ) -> ResponseResult:
        prompt = f"""
Improve the customer-support response using the evaluator feedback.

Original ticket:
{ticket_text}

Category:
{category}

Priority:
{priority}

Current response:
{current_response}

Evaluator feedback:
{feedback}

Requirements:
- Include the category.
- Use the exact phrase "As a next step".
- Use the exact phrase "reference number".
- Do not promise a guaranteed outcome.
- Keep the response under 100 words.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=ResponseResult,
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty revision.")

        return ResponseResult.model_validate_json(response.text)


@lru_cache
def get_llm_service() -> GeminiTicketService:
    return GeminiTicketService()
