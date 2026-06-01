from typing_extensions import TypedDict, Annotated
from langgraph.graph import add_messages
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    summary: str
    query: str 
    rewritten_query: str   
    intent: list       
    retrieval_result: str
    web_search_result: str
    input_tokens: int 
    truncation_count:int 
    summarization_count:int


    
