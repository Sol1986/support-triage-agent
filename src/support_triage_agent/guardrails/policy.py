"""Human-escalation policy for the triage graph, evaluated by `guard_output`.

A declarative table of named rules rather than scattered keyword `if`
statements, so the policy can evolve independently of classification/drafting
prompts — and so it's obvious which specific condition triggered escalation
for any given ticket (see `EscalationDecision.matched_rules`). Not every
keyword hit escalates: each rule targets a specific brief-mandated scenario
(account compromise, fraud, threats, legal complaints, payment-card info,
repeated evaluation failure, max revisions reached, schema/safety failures),
rather than treating any risky-sounding word as an automatic escalation.
"""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, Field

from support_triage_agent.state import MAX_REVISIONS, TicketState

# Keyword groups used by the rules below. Kept here (not in nodes.py) so the
# escalation policy can be tuned without touching classification/priority logic.
_SECURITY_KEYWORDS = [
    "hacked",
    "compromised",
    "unauthorized access",
    "someone else has logged",
    "someone else's logged",
    "suspicious login",
    "did not request this password",
    "wasn't me",
]
_FRAUD_KEYWORDS = [
    "fraud",
    "did not authorize",
    "didn't authorize",
    "unauthorized purchase",
    "unauthorized charge",
]
_THREAT_KEYWORDS = ["threat", "threatening", "extort", "blackmail"]
_LEGAL_KEYWORDS = ["legal action", "lawsuit", "attorney", "sue you", "lawyer"]
_PCI_KEYWORDS = ["card number", "cvv", "credit card number", "card details"]


class EscalationDecision(BaseModel):
    """Outcome of evaluating whether a ticket requires human review."""

    requires_human_review: bool
    reason: str | None = None
    matched_rules: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class EscalationRule:
    rule_id: str
    reason: str
    predicate: Callable[[TicketState, list[str]], bool]


def _keyword_match(ticket_lower: str, keywords: list[str]) -> bool:
    return any(keyword in ticket_lower for keyword in keywords)


def _matches_security_keywords(state: TicketState, flags: list[str]) -> bool:
    return _keyword_match(state["ticket_text"].lower(), _SECURITY_KEYWORDS)


def _matches_fraud_keywords(state: TicketState, flags: list[str]) -> bool:
    return _keyword_match(state["ticket_text"].lower(), _FRAUD_KEYWORDS)


def _matches_threat_keywords(state: TicketState, flags: list[str]) -> bool:
    return _keyword_match(state["ticket_text"].lower(), _THREAT_KEYWORDS)


def _matches_legal_keywords(state: TicketState, flags: list[str]) -> bool:
    return _keyword_match(state["ticket_text"].lower(), _LEGAL_KEYWORDS)


def _matches_pci_keywords(state: TicketState, flags: list[str]) -> bool:
    return _keyword_match(state["ticket_text"].lower(), _PCI_KEYWORDS)


def _prompt_injection_suspected(state: TicketState, flags: list[str]) -> bool:
    return "injection_suspected" in flags


def _repeated_evaluation_failure(state: TicketState, flags: list[str]) -> bool:
    return state["revision_count"] >= MAX_REVISIONS and state["evaluation_score"] < 8


def _schema_validation_failed(state: TicketState, flags: list[str]) -> bool:
    return "schema_validation_failed" in flags or state.get(
        "schema_validation_failed", False
    )


def _safety_block(state: TicketState, flags: list[str]) -> bool:
    return "safety_block" in flags


ESCALATION_RULES: list[EscalationRule] = [
    EscalationRule(
        "account_compromise", "Possible account compromise", _matches_security_keywords
    ),
    EscalationRule(
        "fraud", "Possible fraud or unauthorized charge", _matches_fraud_keywords
    ),
    EscalationRule(
        "threat", "Threat or extortion attempt detected", _matches_threat_keywords
    ),
    EscalationRule(
        "legal_complaint",
        "Legal complaint or threat of legal action",
        _matches_legal_keywords,
    ),
    EscalationRule(
        "payment_card_info",
        "Payment card information mentioned in ticket",
        _matches_pci_keywords,
    ),
    EscalationRule(
        "prompt_injection_suspected",
        "Ticket text flagged as a possible prompt-injection attempt",
        _prompt_injection_suspected,
    ),
    EscalationRule(
        "repeated_evaluation_failure",
        "Draft response failed quality evaluation even after the maximum revisions",
        _repeated_evaluation_failure,
    ),
    EscalationRule(
        "schema_validation_failed",
        "Structured LLM output failed validation",
        _schema_validation_failed,
    ),
    EscalationRule(
        "safety_block", "Gemini safety filter blocked a generation", _safety_block
    ),
]


def evaluate_escalation(state: TicketState, flags: list[str]) -> EscalationDecision:
    """Run every rule in `ESCALATION_RULES`; escalate if any one of them matches."""
    matched = [rule for rule in ESCALATION_RULES if rule.predicate(state, flags)]

    return EscalationDecision(
        requires_human_review=bool(matched),
        reason=matched[0].reason if matched else None,
        matched_rules=[rule.rule_id for rule in matched],
    )
