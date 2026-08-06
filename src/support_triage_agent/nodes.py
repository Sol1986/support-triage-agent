from support_triage_agent.state import TicketState


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
    cleaned_ticket = state["ticket_text"].strip()

    if not cleaned_ticket:
        raise ValueError("Ticket text cannot be empty.")

    if len(cleaned_ticket) < 10:
        raise ValueError(
            "Ticket must contain at least 10 characters."
        )

    return {"ticket_text": cleaned_ticket}


def classify_ticket(state: TicketState) -> dict:
    ticket_lower = state["ticket_text"].lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in ticket_lower for keyword in keywords):
            return {"category": category}

    return {"category": "general"}


def assign_priority(state: TicketState) -> dict:
    ticket_lower = state["ticket_text"].lower()

    if any(
        keyword in ticket_lower
        for keyword in HIGH_PRIORITY_KEYWORDS
    ):
        priority = "high"
    elif any(
        keyword in ticket_lower
        for keyword in MEDIUM_PRIORITY_KEYWORDS
    ):
        priority = "medium"
    else:
        priority = "low"

    return {
        "priority": priority,
        "requires_human_review": True,
    }


def create_summary(state: TicketState) -> dict:
    summary = (
        f"Customer submitted a {state['category']} support request."
    )

    return {"summary": summary}


def draft_response(state: TicketState) -> dict:
    category = state["category"]
    priority = state["priority"]

    response_templates = {
        "high": (
            f"We received your {category} support request and marked "
            "it as high priority. A support specialist will review "
            "the issue."
        ),
        "medium": (
            f"We received your {category} support request. "
            "Our support team will review the issue."
        ),
        "low": (
            f"We received your {category} support request. "
            "Our team will review it."
        ),
    }

    return {
        "draft_response": response_templates[priority],
        "revision_count": 0,
    }


def evaluate_response(state: TicketState) -> dict:
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
            "Response needs improvement. Missing: "
            + ", ".join(missing_elements)
            + "."
        )
    else:
        feedback = "Response meets all required quality checks."

    return {
        "evaluation_score": score,
        "evaluation_feedback": feedback,
    }


def revise_response(state: TicketState) -> dict:
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