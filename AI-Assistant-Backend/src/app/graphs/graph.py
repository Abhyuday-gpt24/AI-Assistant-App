from langgraph.graph import StateGraph, START, END
from src.app.tools.retrieval_tool import (
    user_docs_retrieval_node,
    company_kb_retrieval_node,
)
from src.app.nodes.agent_nodes import query_analyzer_node, synthesizer_agent_node
from src.app.nodes.context_management_node import context_management_node
from src.app.mcp.tavily_search import web_search
from src.app.graphs.graph_state import AgentState
from src.app.nodes.router_nodes import route_after_analysis






def graph_build():
    graph = StateGraph(AgentState)
    graph.add_node("query_analyzer_node", query_analyzer_node)
    graph.add_node("user_docs_retrieval_node", user_docs_retrieval_node)
    graph.add_node("company_kb_retrieval_node", company_kb_retrieval_node)
    graph.add_node("web_search_node", web_search)
    graph.add_node("synthesizer_agent_node", synthesizer_agent_node)
    graph.add_node("context_management_node", context_management_node)

    graph.add_edge(START, "query_analyzer_node")
    graph.add_conditional_edges(
        "query_analyzer_node",
        route_after_analysis,
        # explicit map so LangGraph knows all possible targets
        {
            "synthesizer_agent_node": "synthesizer_agent_node",
            "web_search_node": "web_search_node",
            "user_docs_retrieval_node": "user_docs_retrieval_node",
            "company_kb_retrieval_node": "company_kb_retrieval_node",
        },
    )
    graph.add_edge("user_docs_retrieval_node", "synthesizer_agent_node")
    graph.add_edge("company_kb_retrieval_node", "synthesizer_agent_node")
    graph.add_edge("web_search_node", "synthesizer_agent_node")
    graph.add_edge("synthesizer_agent_node", "context_management_node")  # then check tokens
    graph.add_edge("context_management_node", END)

    return graph


uncompiled_graph = graph_build()




