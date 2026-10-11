from functools import lru_cache

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config import get_settings


@lru_cache
def _client() -> MultiServerMCPClient:
    s = get_settings()
    return MultiServerMCPClient(
        {
            "tavily": {
                "transport": "streamable_http",
                "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={s.tavily_api_key}",
            }
        }
    )


async def get_web_search_tools() -> list:
    """Fetch Tavily's MCP tools, filtered to just search and extract."""
    all_tools = await _client().get_tools()
    allowed = {"tavily_search", "tavily_extract"}
    return [t for t in all_tools if t.name in allowed]