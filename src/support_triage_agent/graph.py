from typing import Literal

from langgraph.graph import END, START, StateGraph

from support_triage_agent.nodes import (
    assign_priority,
    classify_ticket,
    create_summary,
    draft_response,
    evaluate_response,
    revise_response,
    validate_ticket,
)
from support_triage_agent.state import TicketState

MAX_REVISIONS = 2


def route_after_evaluation(
    state: TicketState,
) -> Literal["finish", "revise"]:
    score = state["evaluation_score"]
    revision_count = state["revision_count"]

    if score >= 8:
        return "finish"

    if revision_count >= MAX_REVISIONS:
        return "finish"

    return "revise"


def build_graph():
    graph_builder = StateGraph(TicketState)

    graph_builder.add_node("validate_ticket", validate_ticket)
    graph_builder.add_node("classify_ticket", classify_ticket)
    graph_builder.add_node("assign_priority", assign_priority)
    graph_builder.add_node("create_summary", create_summary)
    graph_builder.add_node("draft_response", draft_response)
    graph_builder.add_node("evaluate_response", evaluate_response)
    graph_builder.add_node("revise_response", revise_response)

    graph_builder.add_edge(START, "validate_ticket")
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
            "finish": END,
            "revise": "revise_response",
        },
    )

    graph_builder.add_edge(
        "revise_response",
        "evaluate_response",
    )

    return graph_builder.compile()


support_graph = build_graph()
