"""Builds the LangGraph state machine that drives ticket triage.

Pipeline: guard_input -> validate -> classify -> assign_priority -> summarize
-> draft -> evaluate -> (finish | revise -> evaluate, looping up to
MAX_REVISIONS times) -> guard_output. `guard_input` can short-circuit
straight to END for a rejected ticket; `guard_output` is where
`requires_human_review` is finally decided.
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from support_triage_agent.nodes import (
    assign_priority,
    classify_ticket,
    create_summary,
    draft_response,
    evaluate_response,
    guard_input,
    guard_output,
    revise_response,
    validate_ticket,
)
from support_triage_agent.state import MAX_REVISIONS, TicketState


def route_after_input_guard(
    state: TicketState,
) -> Literal["reject", "proceed"]:
    """Short-circuit straight to END for a ticket `guard_input` rejected outright."""
    if "input_rejected" in state.get("guardrail_flags", []):
        return "reject"

    return "proceed"


def route_after_evaluation(
    state: TicketState,
) -> Literal["finish", "revise"]:
    """Decide whether the draft is good enough or needs another revision pass."""
    score = state["evaluation_score"]
    revision_count = state["revision_count"]

    if score >= 8:
        return "finish"

    if revision_count >= MAX_REVISIONS:
        return "finish"

    return "revise"


def build_graph() -> CompiledStateGraph:
    """Wire up and compile the triage graph's nodes and edges."""
    graph_builder = StateGraph(TicketState)

    graph_builder.add_node("guard_input", guard_input)
    graph_builder.add_node("validate_ticket", validate_ticket)
    graph_builder.add_node("classify_ticket", classify_ticket)
    graph_builder.add_node("assign_priority", assign_priority)
    graph_builder.add_node("create_summary", create_summary)
    graph_builder.add_node("draft_response", draft_response)
    graph_builder.add_node("evaluate_response", evaluate_response)
    graph_builder.add_node("revise_response", revise_response)
    graph_builder.add_node("guard_output", guard_output)

    graph_builder.add_edge(START, "guard_input")

    graph_builder.add_conditional_edges(
        "guard_input",
        route_after_input_guard,
        {
            "reject": END,
            "proceed": "validate_ticket",
        },
    )

    graph_builder.add_edge(
        "validate_ticket",
        "classify_ticket",
    )
    graph_builder.add_edge(
        "classify_ticket",
        "assign_priority",
    )
    graph_builder.add_edge(
        "assign_priority",
        "create_summary",
    )
    graph_builder.add_edge(
        "create_summary",
        "draft_response",
    )
    graph_builder.add_edge(
        "draft_response",
        "evaluate_response",
    )

    graph_builder.add_conditional_edges(
        "evaluate_response",
        route_after_evaluation,
        {
            "finish": "guard_output",
            "revise": "revise_response",
        },
    )

    graph_builder.add_edge(
        "revise_response",
        "evaluate_response",
    )

    graph_builder.add_edge("guard_output", END)

    return graph_builder.compile()


# Compiled once at import time and reused by pipeline.process_ticket for every request.
support_graph = build_graph()
