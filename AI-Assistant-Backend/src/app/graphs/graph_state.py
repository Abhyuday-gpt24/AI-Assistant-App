from typing_extensions import TypedDict, Annotated
from langgraph.graph import add_messages
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    summary: str
    query: str
    rewritten_query: str
    intent: list
    category: str   # query type (math/code/general) → picks the synthesizer model tier
    user_docs_result: str    # hits from THIS chat's own uploads (intent user_docs)
    company_kb_result: str   # hits from the shared company KB (intent company_kb)
    web_search_result: str
    input_tokens: int
    truncation_count:int
    summarization_count:int
    user_id: str   # the owner; used for S3 paths + chunk metadata
    chat_id: str   # the conversation id (== thread_id); ALSO the RAG scope — it's
                   # the metadata filter retrieval uses inside the tenant namespace
    attachments: list   # files attached this turn — consumed ONLY by the synthesizer node


    
