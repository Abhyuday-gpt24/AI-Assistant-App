from src.app.graphs.graph_state import AgentState
from src.app.models.models import gpt_54_nano_model, groq_gpt_model, deepseek_flash_model
from src.app.sys_prompts.asistant_sys_prompt import QUERY_ANALYZER_SYS_PROMPT,FEW_SHOT_FOR_QUERY_ANALYZER, SYNTHESIZER_AGENT_SYS_PROMPT
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

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
    system_prompt = QUERY_ANALYZER_SYS_PROMPT + f"{FEW_SHOT_FOR_QUERY_ANALYZER}"
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

    sys_prompt = SYNTHESIZER_AGENT_SYS_PROMPT
    sys_prompt += f"\n\nRetrieved context:\n{kb}\n\nWeb search results:\n{web}"
    if summary:
        sys_prompt += f"\n\nPrevious conversation summary:\n{summary}"

    sys_prompt += f"\n\n Current date and time : {current_time()}"

    response = await deepseek_flash_model.ainvoke([
        SystemMessage(sys_prompt),
        *state["messages"],
    ])
    return {"messages": [response]}


    