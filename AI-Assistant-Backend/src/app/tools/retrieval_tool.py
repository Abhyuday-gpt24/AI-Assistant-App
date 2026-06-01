from src.app.rag_pipeline.vector_store import get_retriever
from src.app.graphs.graph_state import AgentState

def retrieve_tool(state: AgentState)-> AgentState:
    retriever = get_retriever()
    query = state.get("reframed_query") or state["query"]
    result = retriever.invoke(query)
    return {"retrieval_result": result}