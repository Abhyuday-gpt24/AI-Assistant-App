"""KB retrieval nodes — two scoped retrievers over the one tenant namespace.

The analyzer splits a KB need into two intents, each with its own metadata scope
and its own state key (so they can fan out in parallel without clobbering each
other): `user_docs` (this chat's own uploads) and `nextjs_docs` (the curated
Next.js documentation corpus). Each node formats its hits with an ORIGIN label so
the synthesizer can attribute/cite them correctly.
"""

from src.app.rag_pipeline.vector_store import (
    get_user_docs_retriever,
    get_nextjs_docs_retriever,
)
from src.app.rag_pipeline.reranker import rerank
from src.app.graphs.graph_state import AgentState


def _query(state: AgentState) -> str:
    # The analyzer's search-optimized rewrite when available, else the raw query.
    return state.get("rewritten_query") or state["query"]


def _format(docs, origin: str) -> str:
    """Format hits into source-attributed text. `origin` is "user" or "nextjs";
    the bracketed label lets the synthesizer cite the right source."""
    blocks = []
    for d in docs:
        meta = d.metadata or {}
        name = meta.get("filename") or meta.get("source", "document")
        trail = meta.get("heading_trail")
        if origin == "nextjs":
            topic = meta.get("topic")
            label = f"Next.js Docs · {topic} · {name}" if topic else f"Next.js Docs · {name}"
        else:
            label = f"Your upload · {name}"
        header = f"{label} > {trail}" if trail else label
        blocks.append(f"[{header}]\n{d.page_content}")
    return "\n\n".join(blocks)


def user_docs_retrieval_node(state: AgentState) -> AgentState:
    """Retrieve from the user's OWN uploads in this chat (scoped by `chat_id`),
    then Cohere-rerank — keeping only chunks above the relevance threshold."""
    chat_id = state.get("chat_id")
    if not chat_id:
        return {"user_docs_result": ""}
    query = _query(state)
    docs = get_user_docs_retriever(chat_id=chat_id).invoke(query)
    docs = rerank(query, docs)
    return {"user_docs_result": _format(docs, "user")}


def nextjs_docs_retrieval_node(state: AgentState) -> AgentState:
    """Retrieve from the curated Next.js documentation KB (`source="company"`, `topic="nextjs"`),
    then Cohere-rerank — keeping only chunks above the relevance threshold."""
    query = _query(state)
    docs = get_nextjs_docs_retriever().invoke(query)
    docs = rerank(query, docs)
    return {"nextjs_docs_result": _format(docs, "nextjs")}
