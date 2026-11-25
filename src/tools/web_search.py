import json
from functools import lru_cache

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config import get_settings

# (max results, max characters of content per result) sent to the LLM
_LIMITS = {
    "tavily_search": (5, 400),
    "tavily_extract": (2, 1500),
}


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


def _trim(tool_name: str, raw) -> str:
    """Keep only title, url and a short content snippet for the top few results."""
    max_results, max_chars = _LIMITS[tool_name]

    # MCP tools return a list of content blocks; the JSON payload is in the first text block
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
        text = raw[0]["text"]
    else:
        text = raw if isinstance(raw, str) else str(raw)

    try:
        data = json.loads(text)
    except Exception:
        return text[: max_results * max_chars]  # not JSON, so hard-cap it

    slim = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": (r.get("content") or r.get("raw_content") or "")[:max_chars],
        }
        for r in data.get("results", [])[:max_results]
    ]
    return json.dumps({"results": slim}, ensure_ascii=False)


def _slim_tool(tool) -> StructuredTool:
    """Same name, description and schema as the MCP tool, but with trimmed output."""

    async def _run(**kwargs) -> str:
        raw = await tool.ainvoke(kwargs)
        return _trim(tool.name, raw)

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        coroutine=_run,
    )


async def get_web_search_tools() -> list:
    """Tavily's MCP tools (search and extract only), with output trimmed for the LLM."""
    all_tools = await _client().get_tools()
    return [_slim_tool(t) for t in all_tools if t.name in _LIMITS]