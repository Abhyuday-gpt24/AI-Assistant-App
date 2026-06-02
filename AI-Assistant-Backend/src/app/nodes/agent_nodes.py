from src.app.graphs.graph_state import AgentState
from src.app.models.models import gpt_54_nano_model, groq_gpt_model, deepseek_flash_model
from src.app.sys_prompts.asistant_sys_prompt import QUERY_ANALYZER_SYS_PROMPT, SYNTHESIZER_AGENT_SYS_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

# Cap how much of each attached document we inline into the synthesizer's
# context (RAG retrieval still covers the wider corpus).
MAX_DOC_CHARS = 24000

# Define the structure
class QueryAnalyzerInterface(BaseModel):
    intent: list[Literal["direct", "kb_retrieve", "web_search"]] = Field(
        description='List of intents: ["kb_retrieve"], ["web_search"], ["direct"], or ["kb_retrieve","web_search"] for parallel retrieval. "direct" is never combined with others.'
    )
    rewritten_query: str = Field(
        description="Search-optimized rewrite of user query. For 'direct' intent, keep original as-is."
    )


gpt_54_nano_structured_output = gpt_54_nano_model.with_structured_output(QueryAnalyzerInterface, include_raw = True)



def current_time()-> datetime:
    now = datetime.now()
    return now

# Query Analyzer Node
async def query_analyzer_node(state: AgentState) -> AgentState:
    summary = state.get("summary", "")
    system_prompt = QUERY_ANALYZER_SYS_PROMPT
    if summary:
        system_prompt += f"\n\nPrevious conversation summary:\n{summary} \n\n Current date and time : {current_time()}"
    response = await gpt_54_nano_structured_output.ainvoke([SystemMessage(system_prompt), *state["messages"]])

    result = response["parsed"]

    token_count = response["raw"].usage_metadata.get("total_tokens", 0) if hasattr(response["raw"], "usage_metadata") else 0


    return {
        "intent": result.intent,
        "rewritten_query": result.rewritten_query,
        "retrieval_result": "",
        "web_search_result": "",
        "input_tokens": token_count
    }


async def synthesizer_agent_node(state: AgentState) -> AgentState:
    kb = state.get("retrieval_result", "")
    web = state.get("web_search_result", "")

    summary = state.get("summary", "")
    attachments = state.get("attachments") or []

    sys_prompt = SYNTHESIZER_AGENT_SYS_PROMPT
    sys_prompt += f"\n\nRetrieved context:\n{kb}\n\nWeb search results:\n{web}"
    if summary:
        sys_prompt += f"\n\nPrevious conversation summary:\n{summary}"

    # Attached-DOCUMENT text is injected here (synthesizer only) — never reaches
    # the query-analyzer node. Each doc carries its converted Markdown.
    docs = [a for a in attachments if a.get("doc_markdown")]
    if docs:
        doc_ctx = "\n\n".join(
            f"--- Attached document: {d.get('original_name', 'document')} ---\n"
            f"{d['doc_markdown'][:MAX_DOC_CHARS]}"
            + ("\n\n[... document truncated ...]" if len(d['doc_markdown']) > MAX_DOC_CHARS else "")
            for d in docs
        )
        sys_prompt += f"\n\nAttached document(s) the user provided this turn:\n{doc_ctx}"

    sys_prompt += f"\n\n Current date and time : {current_time()}"

    # Attached IMAGES are inlined onto the current user turn so the model can see
    # them (also synthesizer-only). Rebuild just the last HumanMessage with image
    # blocks; history is untouched.
    messages = list(state["messages"])
    images = [a for a in attachments if a.get("data_uri")]
    if images and messages and isinstance(messages[-1], HumanMessage):
        last = messages[-1]
        base_text = last.content if isinstance(last.content, str) else ""
        content = [{"type": "text", "text": base_text}]
        for img in images:
            # OpenAI-compatible multimodal format: image_url is an OBJECT.
            content.append({"type": "image_url", "image_url": {"url": img["data_uri"]}})
        messages = messages[:-1] + [HumanMessage(content=content)]

    response = await deepseek_flash_model.ainvoke([
        SystemMessage(sys_prompt),
        *messages,
    ])
    return {"messages": [response]}


    