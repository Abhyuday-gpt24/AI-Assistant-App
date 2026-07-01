import json
import logging
import random
from langchain_core.messages import HumanMessage
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.app.graphs.graph import uncompiled_graph
from config import settings


logger = logging.getLogger(__name__)

DB_URI = settings.SUPABASE_DB_URL


# Ephemeral "thinking" statuses streamed WHILE the graph works, before the answer
# tokens arrive. Emitted once per node as it first runs, so they reflect what the
# agent is ACTUALLY doing (only "Searching the web…" if web search really ran).
# Sent as {"status": …} SSE frames; the frontend shows the latest and clears it
# when the first answer delta arrives. Several variants per stage for personality.
_STATUS_OPENERS = [
    "🤔 Hmm, let me think…",
    "💭 Thinking this through…",
    "🤔 Got it — one sec…",
]
_NODE_STATUS = {
    "query_analyzer_node": [
        "🧐 Clarifying your query…",
        "🧐 Got your point!",
        "🧐 Making sense of that…",
    ],
    "user_docs_retrieval_node": [
        "📄 Digging through your documents…",
        "📄 Skimming your files…",
        "📄 Checking your uploads…",
    ],
    "nextjs_docs_retrieval_node": [
        "📚 Collecting related Next.js docs…",
        "📚 Flipping through the Next.js docs…",
        "📚 Pulling up the relevant docs…",
    ],
    "web_search_node": [
        "🌐 Searching the web…",
        "🌐 Scouting the web…",
        "🌐 Looking that up online…",
    ],
    "synthesizer_agent_node": [
        "✍️ Writing your answer…",
        "✍️ Putting it together…",
        "✍️ Drafting a reply…",
    ],
}


def _status_frame(message: str) -> str:
    return f"data: {json.dumps({'status': message})}\n\n"


async def delete_chat_thread(thread_id: str) -> None:
    """Purge a chat's LangGraph checkpointer state (keyed on thread_id == chat_id)
    from Postgres, so a deleted chat leaves no resumable graph memory behind.
    Best-effort: if the saver can't be reached or the thread has no checkpoints,
    deletion of the rest of the chat must still proceed."""
    try:
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup()
            await checkpointer.adelete_thread(thread_id)
    except Exception:
        logger.warning("Failed to delete checkpointer thread %s", thread_id,
                       exc_info=True)


async def stream_chat(message: str, thread_id: str,
                      attachments: list[dict] | None = None,
                      user_id: str | None = None,
                      has_user_docs: bool = False):
    config = {"configurable": {"thread_id": thread_id}}
    # The user turn stays CLEAN (text only) so the query-analyzer node sees just
    # the request, never the attached file. Attachments ride in their own state
    # field and are consumed ONLY by the synthesizer node (images inline + doc
    # text in its system prompt). Always set it (even []) so a later turn
    # overwrites the checkpointed value instead of replaying old attachments.
    input_data = {
        "messages": [HumanMessage(content=message)],
        "attachments": attachments or [],
        "has_user_docs": has_user_docs,
        "user_docs_result": "",
        "nextjs_docs_result": "",
        "web_search_result": "",
        "intent": "",
        "query": message,
        "rewritten_query": "",
        "user_id": user_id or "",
        # thread_id IS the chat_id — conversation identity / checkpointer key AND
        # the RAG scope (retrieval filters the tenant namespace by this chat_id).
        "chat_id": thread_id,
    }

    try:
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup()
            graph = uncompiled_graph.compile(checkpointer=checkpointer)

            # Immediate feedback the instant the stream opens, before the graph
            # has produced anything.
            yield _status_frame(random.choice(_STATUS_OPENERS))

            seen_nodes: set[str] = set()
            async for event in graph.astream_events(input_data, config=config, version="v2"):
                node = event.get("metadata", {}).get("langgraph_node", "")

                # First time each node runs, surface a playful status for it. Runs
                # in graph order; parallel branches emit their lines as they start.
                if node in _NODE_STATUS and node not in seen_nodes:
                    seen_nodes.add(node)
                    yield _status_frame(random.choice(_NODE_STATUS[node]))

                if event["event"] == "on_chat_model_stream" and node == "synthesizer_agent_node":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'delta': chunk.content})}\n\n"
            yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"