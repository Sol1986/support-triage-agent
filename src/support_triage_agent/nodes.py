"""LangGraph node functions for the support-triage workflow.

Every node takes the full `TicketState` and returns a partial dict of the
fields it updates (LangGraph merges these back into state). When
`state["llm_enabled"]` is true, classification and drafting steps delegate to
Gemini via `llm.py`; otherwise they fall back to the deterministic
keyword/template rules defined below, so the graph always works without an
API key.
"""

from typing import get_args

from support_triage_agent.guardrails import input_guard, output_guard, pii, policy
from support_triage_agent.llm import TicketCategory, get_llm_service
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

# CATEGORY_KEYWORDS covers every classifiable category except "general" (the
# fallback below), so the two must stay in sync or deterministic and
# LLM-backed classification could silently diverge on which categories exist.
assert set(CATEGORY_KEYWORDS) | {"general"} == set(get_args(TicketCategory)), (
    "CATEGORY_KEYWORDS is out of sync with TicketCategory"
)

# Unlike CATEGORY_KEYWORDS, these drive `assign_priority` unconditionally —
# priority is always keyword-based, even when llm_enabled is True.
HIGH_PRIORITY_KEYWORDS = [
    "urgent",
    "immediately",
    "twice",
    "duplicate",
    "locked out",
    "cannot access",
    "outage",
    "completely down",
    "service is down",
    "system is down",
    "can't work",
    "cannot work",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "soon",
    "problem",
    "issue",
    "not working",
]


def guard_input(state: TicketState) -> dict:
    """Screen the raw ticket before it reaches the rest of the pipeline.

    On rejection, `graph.route_after_input_guard` short-circuits straight to
    `END` — the ticket never reaches classification or draft generation, and
    is flagged for human review instead. `nodes.validate_ticket`'s own
    empty/too-short check is unchanged and still runs for tickets that pass
    this screening.
    """
    result = input_guard.check_input(state["ticket_text"])

    if not result.accepted:
        return {
            "guardrail_flags": [*result.flags, "input_rejected"],
            "requires_human_review": True,
            "escalation_reason": result.rejection_reason,
        }

    return {"guardrail_flags": result.flags}


def validate_ticket(state: TicketState) -> dict:
    """Reject empty or too-short ticket text before it reaches classification."""
    cleaned_ticket = state["ticket_text"].strip()

    if not cleaned_ticket:
        raise ValueError("Ticket text cannot be empty.")

    if len(cleaned_ticket) < 10:
        raise ValueError("Ticket must contain at least 10 characters.")

    return {"ticket_text": cleaned_ticket}


def _classify_by_keyword(ticket_text: str) -> str:
    """Deterministic fallback classifier: first matching keyword group wins."""
    ticket_lower = ticket_text.lower()

    # Dict insertion order determines precedence when a ticket matches multiple categories.
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in ticket_lower for keyword in keywords):
            return category

    return "general"


def classify_ticket(state: TicketState) -> dict:
    """Assign a category, via Gemini if enabled, else the first matching keyword group.

    A Gemini structured-output or safety failure falls back to the keyword
    classifier rather than propagating, and flags the fallback for the
    escalation policy (see `guardrails.output_guard`).
    """
    if state["llm_enabled"]:
        service = get_llm_service()
        ticket_text = state["ticket_text"]

        category, guard_flags = output_guard.call_with_fallback(
            lambda: service.classify_ticket(ticket_text).category,
            lambda: _classify_by_keyword(ticket_text),
        )

        if not guard_flags:
            return {"category": category}

        return {
            "category": category,
            "schema_validation_failed": "schema_validation_failed" in guard_flags,
            "guardrail_flags": [*state.get("guardrail_flags", []), *guard_flags],
        }

    return {"category": _classify_by_keyword(state["ticket_text"])}


def assign_priority(state: TicketState) -> dict:
    """Rank urgency from keyword signals.

    Final human-review escalation is decided later by `guard_output`'s
    policy evaluation, not here.
    """
    ticket_lower = state["ticket_text"].lower()

    if any(keyword in ticket_lower for keyword in HIGH_PRIORITY_KEYWORDS):
        priority = "high"
    elif any(keyword in ticket_lower for keyword in MEDIUM_PRIORITY_KEYWORDS):
        priority = "medium"
    else:
        priority = "low"

    return {"priority": priority}


def create_summary(state: TicketState) -> dict:
    """Produce a short internal summary line for the ticket."""
    summary = f"Customer submitted a {state['category']} support request."

    return {"summary": summary}


def _draft_by_template(category: str, priority: str) -> str:
    """Deterministic fallback draft used both when the LLM is disabled and
    when a Gemini call fails its structured-output/safety guardrail."""
    response_templates = {
        "high": (
            f"We received your {category} support request "
            "and marked it as high priority. A support specialist "
            "will review the issue."
        ),
        "medium": (
            f"We received your {category} support request. "
            "Our support team will review the issue."
        ),
        "low": (
            f"We received your {category} support request. Our team will review it."
        ),
    }

    return response_templates[priority]


def draft_response(state: TicketState) -> dict:
    """Write the first customer-facing response, via Gemini if enabled else a template.

    A Gemini structured-output or safety failure falls back to the template
    rather than propagating, and flags the fallback for the escalation policy.
    """
    category = state["category"]
    priority = state["priority"]

    if state["llm_enabled"]:
        service = get_llm_service()
        ticket_text = state["ticket_text"]

        response_text, guard_flags = output_guard.call_with_fallback(
            lambda: (
                service.draft_response(
                    ticket_text=ticket_text,
                    category=category,
                    priority=priority,
                ).response
            ),
            lambda: _draft_by_template(category, priority),
        )

        update = {"draft_response": response_text, "revision_count": 0}
        if guard_flags:
            update["schema_validation_failed"] = (
                "schema_validation_failed" in guard_flags
            )
            update["guardrail_flags"] = [
                *state.get("guardrail_flags", []),
                *guard_flags,
            ]
        return update

    return {
        "draft_response": _draft_by_template(category, priority),
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

    update = {
        "evaluation_score": score,
        "evaluation_feedback": feedback,
    }

    # Written once, on the first pass only, so `evals.harness` can later
    # compare it against the final score to measure revision improvement.
    if state["revision_count"] == 0:
        update["initial_evaluation_score"] = score

    return update


def _revise_by_template(category: str, priority: str) -> str:
    """Deterministic fallback revision: guarantees the exact phrases
    `evaluate_response` checks for, both when the LLM is disabled and when a
    Gemini revision call fails its structured-output/safety guardrail."""
    return (
        f"We received your {category} support request and "
        f"assigned it {priority} priority. As a next step, "
        "a support specialist will review the details and contact "
        "you. Please keep your reference number available for "
        "future communication."
    )


def revise_response(state: TicketState) -> dict:
    """Rewrite the draft to address `evaluate_response` feedback and bump the revision count."""
    category = state["category"]
    priority = state["priority"]

    if state["llm_enabled"]:
        service = get_llm_service()
        ticket_text = state["ticket_text"]
        current_response = state["draft_response"]
        feedback = state["evaluation_feedback"]

        response_text, guard_flags = output_guard.call_with_fallback(
            lambda: (
                service.revise_response(
                    ticket_text=ticket_text,
                    category=category,
                    priority=priority,
                    current_response=current_response,
                    feedback=feedback,
                ).response
            ),
            lambda: _revise_by_template(category, priority),
        )

        update = {
            "draft_response": response_text,
            "revision_count": state["revision_count"] + 1,
        }
        if guard_flags:
            update["schema_validation_failed"] = (
                "schema_validation_failed" in guard_flags
            )
            update["guardrail_flags"] = [
                *state.get("guardrail_flags", []),
                *guard_flags,
            ]
        return update

    return {
        "draft_response": _revise_by_template(category, priority),
        "revision_count": state["revision_count"] + 1,
    }


def guard_output(state: TicketState) -> dict:
    """Finalize the escalation decision and PII-detection flags once the
    evaluate/revise loop has converged.

    This is the only place that sets the real `requires_human_review` value
    for a ticket that made it past `guard_input` — replacing the old
    hardcoded assignment that used to live in `assign_priority`.
    """
    flags = list(state.get("guardrail_flags", []))

    if pii.detect_pii(state["draft_response"]) or pii.detect_pii(state["summary"]):
        flags.append("pii_detected")

    decision = policy.evaluate_escalation(state, flags)

    return {
        "guardrail_flags": flags,
        "requires_human_review": decision.requires_human_review,
        "escalation_reason": decision.reason,
    }
