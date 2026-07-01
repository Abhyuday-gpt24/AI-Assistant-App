
# For MCP Server
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.app.graphs.graph_state import AgentState
from config import settings
from langsmith import traceable



# Tavily MCP Handshake
TAVILY_MCP_LINK = settings.TAVILY_MCP_LINK
if not TAVILY_MCP_LINK:
    raise RuntimeError("Set TAVILY_MCP_LINK in your environment first.")
 
web_search_mcp_client = MultiServerMCPClient(
    {
        "tavily": {
            "url": f"{TAVILY_MCP_LINK}",
            "transport": "streamable_http",
        }
    }
)

web_search_tavily_tool = None
async def load_search_tool():
    global web_search_tavily_tool
    if web_search_tavily_tool is None:
        tools = await web_search_mcp_client.get_tools()
        web_search_tavily_tool = next(t for t in tools if t.name == "tavily_search")



async def web_search(state: AgentState) -> AgentState:
    await load_search_tool()
    
    query = state.get("rewritten_query") or state["query"]
    
    result = await web_search_tavily_tool.ainvoke({"query": query})

    if hasattr(result, "content"):
        content = result.content
    else:
        content = str(result)

    return {"web_search_result": content[:3000]}

