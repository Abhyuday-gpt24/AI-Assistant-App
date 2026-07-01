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
CHARS_PER_TOKEN = 4  # rough English average, for the fallback token estimate


def _content_len(msg) -> int:
    """Character length of a message's text content, tolerating list/multimodal
    content (only text parts count)."""
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for part in content:
            if isinstance(part, str):
                total += len(part)
            elif isinstance(part, dict):
                total += len(str(part.get("text", "")))
        return total
    return len(str(content))


def estimate_tokens(messages, summary: str = "") -> int:
    """Rough token estimate (chars / CHARS_PER_TOKEN) used as a FALLBACK when the
    analyzer's usage_metadata is missing or zero. Without it `input_tokens` could
    be 0 and this node would silently never run, letting history grow until an
    LLM call fails on context length. Undershoots the real count slightly (it
    omits the analyzer's system prompt), which is fine for a safety net."""
    chars = sum(_content_len(m) for m in messages) + len(summary or "")
    return chars // CHARS_PER_TOKEN


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


def adjust_to_human_start(messages, keep_from_index: int) -> int:
    """Move the keep boundary back to the nearest HumanMessage so the RETAINED
    window starts on a user turn. Otherwise summarization can leave the history
    beginning with an AIMessage (its prompting Human turn got summarized away),
    which reads oddly and some providers reject a leading assistant message.
    Falls back to the original index if no earlier Human message exists."""
    for i in range(min(keep_from_index, len(messages) - 1), -1, -1):
        if isinstance(messages[i], HumanMessage):
            return i
    return keep_from_index


async def context_management_node(state: AgentState) -> AgentState:
    # Prefer the analyzer's reported usage; fall back to a chars/4 estimate when
    # it's missing or zero (some providers don't return usage_metadata) so this
    # node never silently no-ops and lets history grow unbounded.
    input_tokens = state.get("input_tokens", 0) or estimate_tokens(
        state["messages"], state.get("summary", "")
    )
    truncation_count = state.get("truncation_count", 0)
    current_truncate_limit = get_current_truncation_limit(truncation_count)
    summarization_count = state.get("summarization_count", 0)
    

    # Full summarization when tokens > 20k
    if input_tokens > BASE_SUMMARIZATION_LIMIT:
        print("========== SUMMARIZATION TRIGGERED (20k+ tokens) ==========")

        messages = state["messages"]
        existing_summary = state.get("summary", "")

        keep_from_index = find_keep_from_index(messages, KEEP_LAST_N_IN_SUMMARIZATION)
        # Ensure the retained window starts on a HumanMessage (a leading AI reply
        # whose user turn was summarized away reads oddly / some providers reject).
        keep_from_index = adjust_to_human_start(messages, keep_from_index)
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