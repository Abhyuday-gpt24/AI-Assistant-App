import json
import logging
from langchain_core.messages import HumanMessage
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.app.graphs.graph import uncompiled_graph
from config import settings


logger = logging.getLogger(__name__)

DB_URI = settings.SUPABASE_DB_URL


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
                      user_id: str | None = None):
    config = {"configurable": {"thread_id": thread_id}}
    # The user turn stays CLEAN (text only) so the query-analyzer node sees just
    # the request, never the attached file. Attachments ride in their own state
    # field and are consumed ONLY by the synthesizer node (images inline + doc
    # text in its system prompt). Always set it (even []) so a later turn
    # overwrites the checkpointed value instead of replaying old attachments.
    input_data = {
        "messages": [HumanMessage(content=message)],
        "attachments": attachments or [],
        "retrieval_result": "",
        "web_search_result": "",
        "intent": "",
        "query": message,
        "rewritten_query": "",
        "user_id": user_id or "",
        # thread_id IS the chat_id; RAG retrieval is scoped to this chat's namespace.
        "chat_id": thread_id,
    }

    try:
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup()
            graph = uncompiled_graph.compile(checkpointer=checkpointer)

            async for event in graph.astream_events(input_data, config=config, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    node = event.get("metadata", {}).get("langgraph_node", "")
                    if node == "synthesizer_agent_node":
                        chunk = event["data"]["chunk"]
                        if hasattr(chunk, "content") and chunk.content:
                            yield f"data: {json.dumps({'delta': chunk.content})}\n\n"
            yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"