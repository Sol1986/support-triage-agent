"""LangGraph node functions for the support-triage workflow.

Every node takes the full `TicketState` and returns a partial dict of the
fields it updates (LangGraph merges these back into state). When
`state["llm_enabled"]` is true, classification and drafting steps delegate to
Gemini via `llm.py`; otherwise they fall back to the deterministic
keyword/template rules defined below, so the graph always works without an
API key.
"""

from support_triage_agent.llm import get_llm_service
from support_triage_agent.state import TicketState

# Keyword lists used for rules-based classification/prioritization when the LLM is disabled.
CATEGORY_KEYWORDS = {
    "billing": [
        "bill",
        "billing",
        "charged",
        "charge",
        "refund",
        "payment",
        "invoice",
    ],
    "technical": [
        "error",
        "broken",
        "crash",
        "login",
        "password",
        "website",
        "app",
    ],
    "account": [
        "account",
        "profile",
        "subscription",
        "cancel",
        "email address",
    ],
    "shipping": [
        "delivery",
        "shipment",
        "shipping",
        "package",
        "arrive",
    ],
}

HIGH_PRIORITY_KEYWORDS = [
    "urgent",
    "immediately",
    "twice",
    "duplicate",
    "locked out",
    "cannot access",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "soon",
    "problem",
    "issue",
    "not working",
]


def validate_ticket(state: TicketState) -> dict:
    """Reject empty or too-short ticket text before it reaches classification."""
    cleaned_ticket = state["ticket_text"].strip()

    if not cleaned_ticket:
        raise ValueError("Ticket text cannot be empty.")

    if len(cleaned_ticket) < 10:
        raise ValueError("Ticket must contain at least 10 characters.")

    return {"ticket_text": cleaned_ticket}


def classify_ticket(state: TicketState) -> dict:
    """Assign a category, via Gemini if enabled, else the first matching keyword group."""
    if state["llm_enabled"]:
        service = get_llm_service()
        result = service.classify_ticket(state["ticket_text"])

        return {"category": result.category}

    ticket_lower = state["ticket_text"].lower()

    # Dict insertion order determines precedence when a ticket matches multiple categories.
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in ticket_lower for keyword in keywords):
            return {"category": category}

    return {"category": "general"}


def assign_priority(state: TicketState) -> dict:
    """Rank urgency from keyword signals; every ticket is flagged for human review."""
    ticket_lower = state["ticket_text"].lower()

    if any(keyword in ticket_lower for keyword in HIGH_PRIORITY_KEYWORDS):
        priority = "high"
    elif any(keyword in ticket_lower for keyword in MEDIUM_PRIORITY_KEYWORDS):
        priority = "medium"
    else:
        priority = "low"

    return {
        "priority": priority,
        # Always true today: every ticket is routed to a human regardless of priority.
        "requires_human_review": True,
    }


def create_summary(state: TicketState) -> dict:
    """Produce a short internal summary line for the ticket."""
    summary = f"Customer submitted a {state['category']} support request."

    return {"summary": summary}


def draft_response(state: TicketState) -> dict:
    """Write the first customer-facing response, via Gemini if enabled else a template."""
    if state["llm_enabled"]:
        service = get_llm_service()

        result = service.draft_response(
            ticket_text=state["ticket_text"],
            category=state["category"],
            priority=state["priority"],
        )

        return {
            "draft_response": result.response,
            "revision_count": 0,
        }

    response_templates = {
        "high": (
            f"We received your {state['category']} support request "
            "and marked it as high priority. A support specialist "
            "will review the issue."
        ),
        "medium": (
            f"We received your {state['category']} support request. "
            "Our support team will review the issue."
        ),
        "low": (
            f"We received your {state['category']} support request. "
            "Our team will review it."
        ),
    }

    return {
        "draft_response": response_templates[state["priority"]],
        "revision_count": 0,
    }


def evaluate_response(state: TicketState) -> dict:
    """Score the draft response against required content checks.

    The score starts at a 4/10 baseline and gains 2 points per check passed,
    so a response hitting all three checks scores 10 and one hitting none
    scores 4. `graph.route_after_evaluation` sends anything under 8 back for
    revision (up to `graph.MAX_REVISIONS` times).
    """
    response = state["draft_response"].lower()

    required_elements = {
        "acknowledges_category": state["category"] in response,
        "explains_next_step": "next step" in response,
        "provides_reference": "reference number" in response,
    }

    passed_checks = sum(required_elements.values())
    score = 4 + (passed_checks * 2)

    missing_elements = [
        name.replace("_", " ")
        for name, passed in required_elements.items()
        if not passed
    ]

    if missing_elements:
        feedback = (
            "Response needs improvement. Missing: " + ", ".join(missing_elements) + "."
        )
    else:
        feedback = "Response meets all required quality checks."

    return {
        "evaluation_score": score,
        "evaluation_feedback": feedback,
    }


def revise_response(state: TicketState) -> dict:
    """Rewrite the draft to address `evaluate_response` feedback and bump the revision count."""
    if state["llm_enabled"]:
        service = get_llm_service()

        result = service.revise_response(
            ticket_text=state["ticket_text"],
            category=state["category"],
            priority=state["priority"],
            current_response=state["draft_response"],
            feedback=state["evaluation_feedback"],
        )

        return {
            "draft_response": result.response,
            "revision_count": state["revision_count"] + 1,
        }

    revised_response = (
        f"We received your {state['category']} support request and "
        f"assigned it {state['priority']} priority. As a next step, "
        "a support specialist will review the details and contact "
        "you. Please keep your reference number available for "
        "future communication."
    )

    return {
        "draft_response": revised_response,
        "revision_count": state["revision_count"] + 1,
    }
