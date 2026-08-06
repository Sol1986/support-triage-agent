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


def validate_ticket(state: TicketState) -> TicketState:
    cleaned_ticket = state.ticket_text.strip()

    if not cleaned_ticket:
        raise ValueError("Ticket text cannot be empty.")

    if len(cleaned_ticket) < 10:
        raise ValueError(
            "Ticket must contain at least 10 characters."
        )

    state.ticket_text = cleaned_ticket
    return state


def classify_ticket(state: TicketState) -> TicketState:
    ticket_lower = state.ticket_text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in ticket_lower for keyword in keywords):
            state.category = category
            return state

    state.category = "general"
    return state


def assign_priority(state: TicketState) -> TicketState:
    ticket_lower = state.ticket_text.lower()

    if any(
        keyword in ticket_lower
        for keyword in HIGH_PRIORITY_KEYWORDS
    ):
        state.priority = "high"
    elif any(
        keyword in ticket_lower
        for keyword in MEDIUM_PRIORITY_KEYWORDS
    ):
        state.priority = "medium"
    else:
        state.priority = "low"

    state.requires_human_review = state.priority == "high"
    return state


def create_summary(state: TicketState) -> TicketState:
    state.summary = (
        f"Customer submitted a {state.category} support request."
    )
    return state


def draft_response(state: TicketState) -> TicketState:
    response_templates = {
        "high": (
            f"Your {state.category} issue has been marked as high "
            "priority. A support specialist will review it as soon "
            "as possible."
        ),
        "medium": (
            f"We received your {state.category} support request. "
            "Our team will review the issue and follow up shortly."
        ),
        "low": (
            f"We received your {state.category} support request. "
            "Our team will review it and provide the appropriate "
            "next steps."
        ),
    }

    state.draft_response = response_templates[state.priority]
    return state