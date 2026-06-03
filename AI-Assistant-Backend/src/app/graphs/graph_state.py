from typing_extensions import TypedDict, Annotated
from langgraph.graph import add_messages
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    summary: str
    query: str
    rewritten_query: str
    intent: list
    category: str   # query type (math/code/general) → picks the synthesizer model tier
    retrieval_result: str
    web_search_result: str
    input_tokens: int
    truncation_count:int
    summarization_count:int
    user_id: str   # the owner; used for S3 paths + ownership, not for RAG scoping
    chat_id: str   # the conversation id (== thread_id); identity, NOT the RAG scope
    rag_namespace: str  # the Pinecone namespace retrieval is scoped to: the
                        # project_id for a project chat (shared corpus), else the
                        # chat_id (isolated). Resolved in the api layer.
    attachments: list   # files attached this turn — consumed ONLY by the synthesizer node


    
