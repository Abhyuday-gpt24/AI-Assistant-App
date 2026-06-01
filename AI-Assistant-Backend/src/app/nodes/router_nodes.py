
from src.app.graphs.graph_state import AgentState
from langgraph.graph import END

def route_after_analysis(state: AgentState) -> str | list[str]:
    intent = state["intent"]
    result = []
    for each_intent in intent:
        if each_intent == "direct":
            result.append("synthesizer_agent_node")
        elif each_intent == "web_search":
            result.append("web_search_node")
        elif each_intent == "kb_retrieve":
            result.append("kb_retrieval_node")

    return result if result else ["synthesizer_agent_node"]