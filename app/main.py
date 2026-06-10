import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.types import Command

from app.agent.runtime import close_agent, get_agent
from app.config import settings
from app.db import engine, get_session
from app.rag.generate import generate
from app.rag.ingest import ingest_file
from app.rag.retrieve import retrieve

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))  # fail fast if DB is down
    yield
    await close_agent()  # close the checkpointer pool
    await engine.dispose()  # return pooled connections


app = FastAPI(title="ops-copilot", lifespan=lifespan)

# USD per 1M tokens (input, output) — for the live cost estimate in the UI
_PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00)}


def _usage(inp: int, out: int, model: str) -> dict:
    pin, pout = _PRICES.get(model, (0.0, 0.0))
    return {
        "type": "usage",
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": inp + out,
        "cost_usd": round(inp / 1e6 * pin + out / 1e6 * pout, 6),
    }

# the browser client is a different origin (:3000) than the API (:8000), so the
# cross-origin fetch needs CORS or it fails with "Failed to fetch"
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestReq(BaseModel):
    path: str


class QueryReq(BaseModel):
    question: str
    k: int = 5
    thread_id: str | None = None


class ResumeReq(BaseModel):
    thread_id: str
    decision: str = "approve"  # "approve" or "deny"


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/model")
async def model_info():
    return {
        "chat_model": settings.chat_model,
        "embed_model": settings.embed_model,
        "local": bool(settings.ollama_base_url),
    }


@app.post("/ingest")
async def ingest(req: IngestReq, session: AsyncSession = Depends(get_session)):
    n = await ingest_file(session, req.path)
    return {"ingested_chunks": n}


@app.post("/query")
async def query(req: QueryReq, session: AsyncSession = Depends(get_session)):
    chunks = await retrieve(session, req.question, k=req.k)
    if not chunks:
        return {"answer": "No documents ingested yet.", "sources": []}
    return await generate(req.question, chunks)


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


async def _stream_run(agent, cfg, agent_input):
    """Stream one agent run (initial or resumed) as typed SSE events. Two stream
    modes at once: "updates" = the trajectory (which tool, each result),
    "messages" = the answer tokens. If the run pauses at the write-approval gate,
    emit an `approval_request` (instead of `done`) so the client can show
    Approve/Deny."""
    in_tok = out_tok = 0
    async for mode, data in agent.astream(
        agent_input, cfg, stream_mode=["updates", "messages"]
    ):
        if mode == "updates":
            for payload in (data or {}).values():
                # an interrupt update carries a tuple, not a {messages: ...} dict
                if not isinstance(payload, dict):
                    continue
                for m in payload.get("messages", []):
                    for call in getattr(m, "tool_calls", None) or []:
                        yield _sse({"type": "tool_call", "name": call["name"],
                                    "args": call["args"]})
                    if m.__class__.__name__ == "ToolMessage":
                        yield _sse({"type": "tool_result",
                                    "name": getattr(m, "name", "tool"),
                                    "content": (m.content or "")[:800]})
        elif mode == "messages":
            chunk, _meta = data
            um = getattr(chunk, "usage_metadata", None)  # rides the final chunk
            if um:
                in_tok += um.get("input_tokens", 0)
                out_tok += um.get("output_tokens", 0)
            if chunk.__class__.__name__ == "AIMessageChunk" and chunk.content:
                yield _sse({"type": "token", "content": chunk.content})

    yield _sse(_usage(in_tok, out_tok, settings.chat_model))
    snap = await agent.aget_state(cfg)
    if snap.next and snap.tasks and snap.tasks[0].interrupts:
        # paused before a write — ask the human (payload is what interrupt() got)
        yield _sse({"type": "approval_request",
                    "thread_id": cfg["configurable"]["thread_id"],
                    **snap.tasks[0].interrupts[0].value})
    else:
        yield _sse({"type": "done"})


@app.post("/agent/stream")
async def agent_stream(req: QueryReq):
    agent = await get_agent()
    thread_id = req.thread_id or str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}
    return StreamingResponse(
        _stream_run(agent, cfg, {"messages": [("user", req.question)]}),
        media_type="text/event-stream",
    )


@app.post("/agent/resume")
async def agent_resume(req: ResumeReq):
    """Resume a paused run after the human decides (approve/deny) on a write."""
    agent = await get_agent()
    cfg = {"configurable": {"thread_id": req.thread_id}}
    return StreamingResponse(
        _stream_run(agent, cfg, Command(resume=req.decision)),
        media_type="text/event-stream",
    )
