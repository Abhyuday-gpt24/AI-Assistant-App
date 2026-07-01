from src.app.graphs.graph_state import AgentState

# intent → node. user_docs / nextjs_docs / web_search may run in parallel (each
# writes its own state key); "direct" goes straight to the synthesizer.
_INTENT_TO_NODE = {
    "direct": "synthesizer_agent_node",
    "user_docs": "user_docs_retrieval_node",
    "nextjs_docs": "nextjs_docs_retrieval_node",
    "web_search": "web_search_node",
}


def route_after_analysis(state: AgentState) -> list[str]:
    # De-dup while preserving order; unknown intents are ignored. Empty → answer
    # directly so the graph never stalls.
    targets = []
    for each_intent in state["intent"]:
        node = _INTENT_TO_NODE.get(each_intent)
        if node and node not in targets:
            targets.append(node)
    return targets or ["synthesizer_agent_node"]
