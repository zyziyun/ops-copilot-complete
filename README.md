# Ops Copilot — complete reference

[![ci](https://github.com/your-org/ops-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/ops-copilot/actions/workflows/ci.yml)

Live URL: _<your-render-url>_ &nbsp;·&nbsp; replace the badge `your-org/ops-copilot` with your repo.

An internal Ops/Support Copilot: a LangGraph ReAct agent that retrieves ops
runbooks (RAG over pgvector + Postgres full-text), inspects live Postgres state
with read-only tools, proposes corrective actions gated by **human approval**,
survives restarts via **durable execution** (Postgres checkpointer), and exposes
its tools through **two self-built MCP servers**. Built across four chapters
(C1–C4) of a 4-hour course.

We build in Python because that is the language of AI-native engineering roles
and AI system design. For your LeetCode coding rounds, use whatever language you
are fastest in — that is a separate track.

## Stack

Python 3.12 · FastAPI (async) · PostgreSQL 16 + pgvector · SQLAlchemy 2 async +
asyncpg · Alembic · OpenAI (`text-embedding-3-small`, `gpt-4o-mini`) · LangGraph
+ `AsyncPostgresSaver` · FastMCP (Streamable HTTP) · Tavily web search · Next.js
streaming client · Docker + gunicorn/uvicorn · GitHub Actions · Render.

## Prerequisites

- Python 3.12, Docker Desktop running, Node 20+ (only for the web client)
- An OpenAI API key with a few dollars of credit
- A Tavily API key (free tier) for web search (C3)

## Quickstart (reproduces the end-to-end sequence)

```bash
# 0. config
cp .env.example .env            # paste your real OPENAI_API_KEY + SEARCH_API_KEY

# 1. deps + database
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d            # Postgres 16 + pgvector

# 2. schema
alembic upgrade head            # extension + chunks + HNSW + tsvector/GIN + tickets

# 3. corpus → embed + store (idempotent)
python scripts/fetch_corpus.py  # writes data/*.md with source_system front-matter
python scripts/ingest_all.py    # or: curl -X POST :8000/ingest per file (see below)

# 4. measure retrieval (prints dense vs hybrid numbers + per-type breakdown)
python -m eval.run_eval

# 5. serve
uvicorn app.main:app --port 8000   # /health /ingest /query /agent/stream

# 6. tests (the safety net: fusion, HITL, durable, injection run offline)
pytest -q
```

Per-file ingest over HTTP (alternative to `ingest_all.py`):

```bash
curl -s -X POST localhost:8000/ingest -H "content-type: application/json" \
  -d '{"path":"data/postgres.md"}'
```

Query and prove grounded refusal:

```bash
curl -s -X POST localhost:8000/query -H "content-type: application/json" \
  -d '{"question":"How do I configure pg_hba.conf authentication?"}'

curl -s -X POST localhost:8000/query -H "content-type: application/json" \
  -d '{"question":"What is ACME stock price today?"}'   # should say it does not know
```

### What `pytest` runs offline vs in CI

`pytest` on a bare clone (no Docker, no OpenAI) runs the deterministic suite:
`test_fusion`, `test_hitl`, `test_durable`, `test_injection` (a scripted fake
chat model + monkeypatched tools — no network). Tests that need Postgres
(`test_tools`, keyword search) or a real OpenAI key (`test_retrieval`,
`eval --gate`) **skip** locally and **run in CI**, where a pgvector service and
secrets are available.

## The agent demo line (C3)

> Alert: Postgres connections near max → retrieve runbook → if no internal
> result, web search → inspect connections + slow queries (read-only) → propose
> terminating a stuck query (write) → **pause for approval** → on approve,
> execute and file a ticket → resumable if the process dies mid-flight.

```python
import asyncio
from langgraph.types import Command
from app.agent.runtime import get_agent

async def demo():
    agent = await get_agent()
    cfg = {"configurable": {"thread_id": "incident-42"}}
    await agent.ainvoke(
        {"messages": [("user", "kill the stuck query on pid 8123")]}, cfg)
    snap = await agent.aget_state(cfg)
    assert snap.next == ("approval",)        # paused, nothing terminated yet
    await agent.ainvoke(Command(resume="approve"), cfg)   # now it runs

asyncio.run(demo())
```

## MCP servers

```bash
python -m mcp_servers.ops_server      # "ops-internal" over Streamable HTTP
python -m mcp_servers.search_server   # "ops-search" (Tavily)
```

Inspect with the MCP Inspector, or connect by URL from Cursor / Claude Desktop.
Internet-facing servers should add bearer-token auth (OAuth 2.1 is the
production target per the 2025-11-25 MCP spec).

## Deploy (Render)

`render.yaml` defines a Docker web service, a managed Postgres, `healthCheckPath:
/health`, secrets with `sync: false`, and `preDeployCommand: alembic upgrade
head`. CI (`needs: test`) deploys only on green.

## Corpus sources and licenses

- GitLab Runbooks — MIT License — https://gitlab.com/gitlab-com/runbooks
- PostgreSQL documentation — PostgreSQL License — https://www.postgresql.org/docs/
- FastAPI documentation — MIT License — https://github.com/fastapi/fastapi
- Django documentation — BSD 3-Clause License — https://github.com/django/django

Each source retains its original copyright. This repository redistributes
excerpts for educational purposes under the terms of the respective licenses.

Full license texts are in [`THIRD_PARTY_LICENSES/`](THIRD_PARTY_LICENSES/). None
of the four imposes copyleft, so your own project code may carry any license.
