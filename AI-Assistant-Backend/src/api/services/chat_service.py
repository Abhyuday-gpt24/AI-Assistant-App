import json
from langchain_core.messages import HumanMessage
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.app.graphs.graph import uncompiled_graph 
from config import settings


DB_URI = settings.SUPABASE_DB_URL



async def stream_chat(message: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {
        "messages": [HumanMessage(content=message)],
        "retrieval_result": "",
        "web_search_result": "",
        "intent": "",
        "query": message,
        "reframed_query": "",
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