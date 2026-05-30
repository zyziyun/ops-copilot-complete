"""Ops tools, in two layers.

1. Plain async functions that take an ``AsyncSession`` — these carry the real
   logic and are what the unit tests exercise directly (test_tools.py).
2. LangChain ``@tool`` wrappers that open their *own* session and expose only
   the business arguments to the model. ToolNode runs these; the model never
   sees or supplies a ``session``.

The write tools live behind the human-approval gate in graph.py. ``WRITE_TOOLS``
is the single source of truth for "this needs approval".
"""
import os

import httpx
from langchain_core.tools import tool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.db import SessionLocal
from app.rag.hybrid import hybrid_search


# --- internal RAG tool ---
async def search_runbooks(session: AsyncSession, query: str) -> str:
    """Search internal runbooks and docs for how to handle an ops symptom."""
    chunks = await hybrid_search(session, query, k=4)
    if not chunks:
        return "NO_INTERNAL_RESULTS"  # signal the agent to try web search
    return "\n\n".join(f"[{c.source}] {c.content[:400]}" for c in chunks)


# --- read-only ops tools (safe, auto-execute) ---
async def get_db_connections(session: AsyncSession) -> str:
    """Return current connection count and the max allowed."""
    row = (
        await session.execute(
            text(
                "SELECT count(*) AS used, "
                "current_setting('max_connections')::int AS max FROM pg_stat_activity"
            )
        )
    ).one()
    return f"connections: {row.used}/{row.max}"


async def get_slow_queries(session: AsyncSession) -> str:
    """Return currently active queries running longer than 5 seconds."""
    rows = (
        await session.execute(
            text(
                "SELECT pid, now()-query_start AS dur, left(query,80) AS q "
                "FROM pg_stat_activity WHERE state='active' "
                "AND now()-query_start > interval '5 seconds' ORDER BY dur DESC LIMIT 5"
            )
        )
    ).all()
    return "\n".join(f"pid={r.pid} dur={r.dur} q={r.q}" for r in rows) or "none"


# --- write tools (require approval, see graph.approval_node) ---
WRITE_TOOLS = {"terminate_query", "create_ticket", "restart_service"}


async def terminate_query(session: AsyncSession, pid: int) -> str:
    """Terminate a stuck backend query by pid. WRITE ACTION."""
    await session.execute(
        text("SELECT pg_terminate_backend(:pid)"), {"pid": pid}
    )
    await session.commit()
    return f"terminated pid {pid}"


async def create_ticket(session: AsyncSession, title: str, severity: str) -> str:
    """File an incident ticket. WRITE ACTION."""
    row = (
        await session.execute(
            text(
                "INSERT INTO tickets(title, severity, created_at) "
                "VALUES (:t, :s, now()) RETURNING id"
            ),
            {"t": title, "s": severity},
        )
    ).one()
    await session.commit()
    return f"created ticket #{row.id}"


async def restart_service(session: AsyncSession, service: str) -> str:
    """Request a restart of an ops service. WRITE ACTION.

    There is no real orchestrator in the course, so this is a simulated action
    that returns a confirmation string. The point is that it is a *write* and
    therefore passes through the approval gate like the others.
    """
    return f"restart requested for service '{service}'"


# --- web search, with a tenacity reliability wrapper (C3 Step 6) ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=8))
async def _tavily_search(query: str, max_results: int = 3) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": os.environ.get("SEARCH_API_KEY", ""),
                "query": query,
                "max_results": max_results,
            },
        )
        r.raise_for_status()
        return [
            {"title": h["title"], "url": h["url"], "content": h["content"]}
            for h in r.json()["results"]
        ]


# ---------------------------------------------------------------------------
# LangChain tool wrappers — these are what the agent binds and ToolNode runs.
# Each opens its own session; the model only supplies business arguments.
# ---------------------------------------------------------------------------
@tool("search_runbooks")
async def search_runbooks_tool(query: str) -> str:
    """Search internal runbooks and docs for how to handle an ops symptom."""
    async with SessionLocal() as s:
        return await search_runbooks(s, query)


@tool("get_db_connections")
async def get_db_connections_tool() -> str:
    """Return the current Postgres connection count and the max allowed."""
    async with SessionLocal() as s:
        return await get_db_connections(s)


@tool("get_slow_queries")
async def get_slow_queries_tool() -> str:
    """Return active queries running longer than 5 seconds."""
    async with SessionLocal() as s:
        return await get_slow_queries(s)


@tool("terminate_query")
async def terminate_query_tool(pid: int) -> str:
    """Terminate a stuck backend query by pid. WRITE ACTION (needs approval)."""
    async with SessionLocal() as s:
        return await terminate_query(s, pid)


@tool("create_ticket")
async def create_ticket_tool(title: str, severity: str) -> str:
    """File an incident ticket. WRITE ACTION (needs approval)."""
    async with SessionLocal() as s:
        return await create_ticket(s, title, severity)


@tool("restart_service")
async def restart_service_tool(service: str) -> str:
    """Request a restart of an ops service. WRITE ACTION (needs approval)."""
    async with SessionLocal() as s:
        return await restart_service(s, service)


@tool("web_search")
async def web_search_tool(query: str) -> str:
    """Search the public web for the latest fix to an error or symptom.

    Use this only when ``search_runbooks`` returns NO_INTERNAL_RESULTS.
    """
    try:
        results = await _tavily_search(query)
    except Exception:
        return "WEB_SEARCH_UNAVAILABLE: I could not reach the web; rely on runbooks."
    return "\n\n".join(
        f"[{r['title']}] {r['content']}" for r in results
    ) or "NO_WEB_RESULTS"


TOOLS = [
    search_runbooks_tool,
    get_db_connections_tool,
    get_slow_queries_tool,
    terminate_query_tool,
    create_ticket_tool,
    restart_service_tool,
    web_search_tool,
]
