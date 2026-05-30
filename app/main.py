import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


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


@app.post("/agent/stream")
async def agent_stream(req: QueryReq):
    agent = await get_agent()
    thread_id = req.thread_id or str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}

    async def event_gen():
        async for chunk in agent.astream(
            {"messages": [("user", req.question)]}, cfg, stream_mode="messages"
        ):
            token = getattr(chunk[0], "content", "")
            if token:
                yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
