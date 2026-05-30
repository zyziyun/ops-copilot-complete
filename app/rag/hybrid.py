import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import embed_texts
from app.models import Chunk
from app.rag.fusion import rrf_merge
from app.rag.keyword import keyword_search
from app.rag.rerank import llm_rerank


async def _vector_search(session, q_emb, k, source_system=None):
    stmt = select(Chunk).order_by(Chunk.embedding.cosine_distance(q_emb)).limit(k)
    if source_system:
        stmt = stmt.where(Chunk.source_system == source_system)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def hybrid_search(
    session: AsyncSession,
    query: str,
    k: int = 5,
    fetch_k: int = 20,
    source_system: str | None = None,
    rerank: bool = False,
) -> list[Chunk]:
    q_emb = (await embed_texts([query]))[0]
    vec, kw = await asyncio.gather(
        _vector_search(session, q_emb, fetch_k, source_system),
        keyword_search(session, query, fetch_k),
        return_exceptions=True,
    )
    # a failed arm degrades to empty rather than killing the whole query
    vec = vec if isinstance(vec, list) else []
    kw = kw if isinstance(kw, list) else []
    fused = rrf_merge([vec, kw], top_n=fetch_k if rerank else k)
    if rerank and fused:
        return await llm_rerank(query, fused, top_n=k)
    return fused[:k]
