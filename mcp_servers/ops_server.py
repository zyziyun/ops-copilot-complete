"""MCP server 1 — internal ops tools, over Streamable HTTP.

FastMCP turns each ``@mcp.tool()`` function into a tool: the function name
becomes the tool name, type hints become the input schema, the docstring becomes
the description. Each tool opens its own DB session and reuses the C2/C3 logic,
so the agent does not care that these tools live behind MCP.
"""
import os

from mcp.server.fastmcp import FastMCP

from app.agent.tools import get_db_connections, get_slow_queries, search_runbooks
from app.db import SessionLocal

# distinct port from the API (8000) and the search server (8002), so all three
# can run side by side locally and in compose
mcp = FastMCP(
    "ops-internal",
    host=os.environ.get("MCP_HOST", "0.0.0.0"),
    port=int(os.environ.get("OPS_MCP_PORT", "8001")),
)


@mcp.tool()
async def search_runbooks_tool(query: str) -> str:
    """Search internal runbooks and docs for an ops symptom."""
    async with SessionLocal() as session:
        return await search_runbooks(session, query)


@mcp.tool()
async def db_connections() -> str:
    """Current Postgres connection count vs max."""
    async with SessionLocal() as session:
        return await get_db_connections(session)


@mcp.tool()
async def slow_queries() -> str:
    """Active queries running longer than 5 seconds."""
    async with SessionLocal() as session:
        return await get_slow_queries(session)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
