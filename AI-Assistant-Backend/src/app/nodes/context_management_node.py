from src.app.graphs.graph_state import AgentState
from src.app.models.models import gpt_5_nano_model
from src.app.sys_prompts.conv_summarizer_sys_prompt import CONV_SUMMARIZER_SYS_PROMPT
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, RemoveMessage

BASE_TRUNCATION_LIMIT = 10000
TRUNCATION_MULTIPLIER = 1.25
BASE_SUMMARIZATION_LIMIT = 20000
KEEP_LAST_N_IN_SUMMARIZATION = 7
KEEP_LAST_N_IN_TRUNCATION = 5
SUMMARIZATION_WORD_LIMIT = 1000
max_chars = 250


def truncate_text(text: str):
    """Truncate at sentence boundary, preserving 1-2 complete sentences."""
    if len(text) <= max_chars:
        return text

    for sep in ['. ', '.\n', '! ', '?\n', '? ']:
        idx = text[:max_chars].rfind(sep)
        if idx > 50:
            return text[:idx + 1] + " [truncated]"

    idx = text[:max_chars].rfind(' ')
    if idx > 0:
        return text[:idx] + "... [truncated]"

    return text[:max_chars] + "... [truncated]"


def truncate_history_msgs(state: AgentState):
    truncated_msgs = []
    msgs = state["messages"]
    for msg in msgs[:-KEEP_LAST_N_IN_TRUNCATION]:
        if not isinstance(msg, (AIMessage, HumanMessage)):
            continue
        if "[truncated]" in msg.content:
            continue
        content = msg.content if len(msg.content) < max_chars else truncate_text(text=msg.content)
        if isinstance(msg, AIMessage):
            truncated_msgs.append(AIMessage(id=msg.id, response_metadata=msg.response_metadata, content=content))
        if isinstance(msg, HumanMessage):
            truncated_msgs.append(HumanMessage(id=msg.id, content=content))

    return truncated_msgs


def get_current_truncation_limit(truncation_count: int) -> float:
    """Calculate the current truncation limit based on how many truncations have occurred."""
    return BASE_TRUNCATION_LIMIT * (TRUNCATION_MULTIPLIER ** truncation_count)


def find_keep_from_index(messages, KEEP_LAST_N_IN_SUMMARIZATION: int) -> int:
    """Find the index from which to keep the last N safe (non-tool) messages."""
    safe_count = 0
    fallback_index = 0
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        has_tool_calls = hasattr(msg, "tool_calls") and msg.tool_calls
        has_tool_call_id = hasattr(msg, "tool_call_id") and msg.tool_call_id

        if not has_tool_calls and not has_tool_call_id:
            safe_count += 1
            if safe_count == 2:
                fallback_index = i
            if safe_count >= KEEP_LAST_N_IN_SUMMARIZATION:
                return i
            
    return fallback_index


async def context_management_node(state: AgentState) -> AgentState:
    input_tokens = state["input_tokens"]
    truncation_count = state.get("truncation_count", 0)
    current_truncate_limit = get_current_truncation_limit(truncation_count)
    summarization_count = state.get("summarization_count", 0)
    

    # Full summarization when tokens > 20k
    if input_tokens > BASE_SUMMARIZATION_LIMIT:
        print("========== SUMMARIZATION TRIGGERED (20k+ tokens) ==========")

        messages = state["messages"]
        existing_summary = state.get("summary", "")

        keep_from_index = find_keep_from_index(messages, KEEP_LAST_N_IN_SUMMARIZATION)
        msgs_to_summarize = messages[:keep_from_index]

        if not msgs_to_summarize:
            return {}

        if existing_summary:
            user_prompt = (
                f"Previous conversation summary:\n{existing_summary}\n\n"
                "Extend the previous summary with this new chat history. "
                F"Summarize the whole conversation in {SUMMARIZATION_WORD_LIMIT} words only. "
                "Keep it concise."
            )
        else:
            user_prompt = (
                "I have given you chat history of the user. "
                f"Summarize the whole conversation in {SUMMARIZATION_WORD_LIMIT} words only. "
                "Keep it concise."
            )

        response = await gpt_5_nano_model.ainvoke([
            SystemMessage(CONV_SUMMARIZER_SYS_PROMPT),
            *msgs_to_summarize,
            HumanMessage(user_prompt),
        ])

        snapshot_ids = {m.id for m in msgs_to_summarize}
        delete_ops = [RemoveMessage(id=m.id) for m in messages if m.id in snapshot_ids]

        print(f"SUMMARY (kept last {len(messages) - keep_from_index} msgs): {response.content[:200]}...")

        return {
            "messages": delete_ops,
            "summary": response.content,
            "truncation_count": 0,  # reset after summarization
            "summarization_count": summarization_count + 1
        }

    if input_tokens > current_truncate_limit:
        
        print(f"--- TRUNCATION #{truncation_count + 1} (limit was {current_truncate_limit:.0f}) ---")

        truncated_msgs = truncate_history_msgs(state)
        
        return {
            "messages": truncated_msgs,
            "truncation_count": truncation_count + 1,
        }
    

    return {}