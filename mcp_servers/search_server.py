"""MCP server 2 — public web search via Tavily, over Streamable HTTP."""
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ops-search",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("SEARCH_MCP_PORT", "8002")),
)


@mcp.tool()
async def web_search(query: str, max_results: int = 3) -> list[dict]:
    """Search the public web for the latest fix to an error or symptom."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": os.environ["SEARCH_API_KEY"],
                "query": query,
                "max_results": max_results,
            },
        )
        r.raise_for_status()
        return [
            {"title": h["title"], "url": h["url"], "content": h["content"]}
            for h in r.json()["results"]
        ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
