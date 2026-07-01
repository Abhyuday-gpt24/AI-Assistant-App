from src.app.graphs.graph_state import AgentState
from src.app.models.models import (
    deepseek_flash_model,
    deepseek_pro_model,
    gpt_5_model,
    gpt_5_mini_model,
    gemini_flash_model,
)
from src.app.sys_prompts.asistant_sys_prompt import QUERY_ANALYZER_SYS_PROMPT, SYNTHESIZER_AGENT_SYS_PROMPT
from src.app.rag_pipeline.attachment_selector import select_relevant_doc_text
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

# Cap how much of each attached document we inline into the synthesizer's
# context (RAG retrieval still covers the wider corpus).
MAX_DOC_CHARS = 24000

# Category → synthesizer model (primary `.with_fallbacks([...])` secondary, so a
# provider error on the primary auto-retries on the fallback). Image turns bypass
# this map entirely (handled structurally below — vision model).
#   math    : deepseek-v4-pro    → gpt-5
#   code    : deepseek-v4-pro    → gpt-5
#   general : deepseek-v4-flash  (no fallback; default + the .get() fallback)
CATEGORY_MODELS = {
    "math": deepseek_pro_model.with_fallbacks([gpt_5_model]),
    "code": deepseek_pro_model.with_fallbacks([gpt_5_model]),
    "general": deepseek_flash_model,
}

# Image turns: gemini-2.5-flash (vision) primary → gpt-5-mini fallback on a
# provider error.
VISION_MODEL = gemini_flash_model.with_fallbacks([gpt_5_mini_model])

# Define the structure
class QueryAnalyzerInterface(BaseModel):
    intent: list[Literal["direct", "user_docs", "nextjs_docs", "web_search"]] = Field(
        description='List of intents. "direct" = answer alone (used ALONE). "user_docs" = the user\'s OWN uploaded files in this chat. "nextjs_docs" = the curated Next.js documentation knowledge base (App Router, routing, server/client components, data fetching, config, etc.). "web_search" = live internet info. user_docs / nextjs_docs / web_search MAY be combined (e.g. ["user_docs","nextjs_docs"] to check the user\'s file against the Next.js docs); "direct" is never combined.'
    )
    rewritten_query: str = Field(
        description="Search-optimized rewrite of user query. For 'direct' intent, keep original as-is."
    )
    category: Literal["math", "code", "general"] = Field(
        description='Query TYPE, used to pick the answering model (independent of intent). "math" = calculations/equations/proofs/quantitative reasoning; "code" = programming/debugging/technical implementation; "general" = everything else. For short follow-ups, inherit the prior turn\'s category from the conversation.'
    )


# Analyzer runs every turn and is the critical routing node — it needs RELIABLE
# structured output. DeepSeek was flaky at this and kept falling back (lag + cost),
# so the analyzer now runs on gpt-5-mini (strong structured output) →
# gemini-2.5-flash fallback. Each link is the same structured-output runnable, so
# the {raw, parsed, parsing_error} shape and usage_metadata stay identical no
# matter which model answers.
query_analyzer_structured = gpt_5_mini_model.with_structured_output(
    QueryAnalyzerInterface, include_raw=True
).with_fallbacks([
    gemini_flash_model.with_structured_output(QueryAnalyzerInterface, include_raw=True),
])



def current_time()-> datetime:
    now = datetime.now()
    return now

# Query Analyzer Node
async def query_analyzer_node(state: AgentState) -> AgentState:
    summary = state.get("summary", "")
    system_prompt = QUERY_ANALYZER_SYS_PROMPT
    # When the chat already holds uploaded documents, nudge the router to consider
    # the user's OWN files for content questions. The analyzer only sees clean
    # text and can't otherwise tell a file was uploaded on an earlier turn, so a
    # follow-up like "what does section 12 say?" would fall to "direct" and miss
    # the doc. Retrieval is cheap and returns nothing if nothing matches.
    if state.get("has_user_docs"):
        system_prompt += (
            "\n\nCONTEXT: The user has uploaded one or more documents to THIS chat. "
            "If the latest message could be about document content — a section/page/"
            "chapter/table, \"the document/file/report\", \"what does it say\", a summary, "
            "or anything that might live in an uploaded file — INCLUDE \"user_docs\" in "
            "the intent (combined with other intents as needed)."
        )
    if summary:
        system_prompt += f"\n\nPrevious conversation summary:\n{summary} \n\n Current date and time : {current_time()}"
    response = await query_analyzer_structured.ainvoke([SystemMessage(system_prompt), *state["messages"]])

    result = response["parsed"]

    token_count = response["raw"].usage_metadata.get("total_tokens", 0) if hasattr(response["raw"], "usage_metadata") else 0

    # Deterministic guarantee: if a DOCUMENT was attached on THIS turn, user_docs
    # retrieval must run no matter how the analyzer routed — otherwise a doc
    # question could fall to "direct" and ignore the file. (Same-turn the file may
    # not be indexed yet; the synthesizer's query-aware inline covers that.)
    intents = list(result.intent or [])
    has_attached_doc = any(a.get("doc_markdown") for a in (state.get("attachments") or []))
    if has_attached_doc:
        intents = [i for i in intents if i != "direct"]
        if "user_docs" not in intents:
            intents.append("user_docs")
    if not intents:
        intents = ["direct"]

    return {
        "intent": intents,
        "rewritten_query": result.rewritten_query,
        "category": result.category,
        "user_docs_result": "",
        "nextjs_docs_result": "",
        "web_search_result": "",
        "input_tokens": token_count
    }


async def synthesizer_agent_node(state: AgentState) -> AgentState:
    user_docs = state.get("user_docs_result", "")
    nextjs_docs = state.get("nextjs_docs_result", "")
    web = state.get("web_search_result", "")

    summary = state.get("summary", "")
    attachments = state.get("attachments") or []

    sys_prompt = SYNTHESIZER_AGENT_SYS_PROMPT
    # Only append non-empty context sections so the model isn't handed empty headers.
    if user_docs:
        sys_prompt += f"\n\nYour uploaded documents (this chat):\n{user_docs}"
    if nextjs_docs:
        sys_prompt += f"\n\nNext.js documentation:\n{nextjs_docs}"
    if web:
        sys_prompt += f"\n\nWeb search results:\n{web}"
    if summary:
        sys_prompt += f"\n\nPrevious conversation summary:\n{summary}"

    # Attached-DOCUMENT text is injected here (synthesizer only) — never reaches
    # the query-analyzer node. Each doc carries its converted Markdown; for a doc
    # larger than MAX_DOC_CHARS we inject the parts most RELEVANT to the question
    # (query-aware selection) instead of just the opening pages, so "ask about the
    # rest of the document" works even before RAG indexing finishes.
    docs = [a for a in attachments if a.get("doc_markdown")]
    if docs:
        query = state.get("rewritten_query") or state.get("query") or ""
        blocks = []
        for d in docs:
            full = d["doc_markdown"]
            selected = select_relevant_doc_text(full, query, MAX_DOC_CHARS)
            note = ("" if len(full) <= MAX_DOC_CHARS else
                    "\n\n[Note: large document — the excerpts above are the parts most relevant to "
                    "the question; ask about a specific section for more.]")
            blocks.append(
                f"--- Attached document: {d.get('original_name', 'document')} ---\n{selected}{note}"
            )
        sys_prompt += "\n\nAttached document(s) the user provided this turn:\n" + "\n\n".join(blocks)

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

    # Model selection is two-layered:
    #  1. STRUCTURAL (deterministic): image turns must use a vision-capable model.
    #     DeepSeek is text-only and 400s on image_url blocks ("unknown variant
    #     image_url, expected text"); gemini-2.5-flash / gpt-5-mini accept them.
    #  2. CATEGORY (from the analyzer): math/code → strong DeepSeek Pro reasoner
    #     (→ gpt-5 fallback), general (and any unknown/missing value) → cheap
    #     DeepSeek Flash.
    # All models stream identically, so the SSE contract is unchanged.
    if images:
        model = VISION_MODEL
    else:
        category = state.get("category") or "general"
        model = CATEGORY_MODELS.get(category, deepseek_flash_model)

    response = await model.ainvoke([
        SystemMessage(sys_prompt),
        *messages,
    ])
    return {"messages": [response]}


    