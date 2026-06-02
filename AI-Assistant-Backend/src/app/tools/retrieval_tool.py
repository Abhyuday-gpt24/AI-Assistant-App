from src.app.rag_pipeline.vector_store import get_retriever
from src.app.graphs.graph_state import AgentState

def retrieve_tool(state: AgentState)-> AgentState:
    # RAG is per-user: retrieval is scoped to the user's own namespace. With no
    # user_id there's no knowledge base to search, so return an empty result.
    user_id = state.get("user_id")
    if not user_id:
        return {"retrieval_result": ""}
    retriever = get_retriever(namespace=user_id)
    # Use the analyzer's search-optimized rewrite when available, else the raw query.
    query = state.get("rewritten_query") or state["query"]
    docs = retriever.invoke(query)

    # Format into clean, source-attributed text for the synthesizer (instead of
    # str()-ing a list of Document objects into the prompt).
    blocks = []
    for d in docs:
        source = d.metadata.get("source", "document")
        trail = d.metadata.get("heading_trail")
        header = f"{source} > {trail}" if trail else source
        blocks.append(f"[{header}]\n{d.page_content}")
    return {"retrieval_result": "\n\n".join(blocks)}