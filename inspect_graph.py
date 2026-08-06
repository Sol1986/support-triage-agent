from support_triage_agent.graph import support_graph


initial_state = {
    "ticket_text": (
        "I was charged twice and need a refund immediately."
    ),
    "category": "",
    "priority": "",
    "summary": "",
    "draft_response": "",
    "evaluation_score": 0,
    "evaluation_feedback": "",
    "revision_count": 0,
    "requires_human_review": False,
}


for event in support_graph.stream(
    initial_state,
    stream_mode="updates",
):
    print(event)