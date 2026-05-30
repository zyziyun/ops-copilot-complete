"""Advanced retriever: the C2 hybrid core + structured metadata filtering, HyDE,
and multi-query rewriting. Kept separate so the taught ``hybrid_search`` stays
the clean teaching version; this is the "production knobs" layer on top.
"""
import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import embed_texts
from app.models import Chunk
from app.rag.fusion import rrf_merge
from app.rag.rerank import llm_rerank
from app.rag.rewrite import hyde_embedding, rewrite_query


def _scoped(stmt, source_system: str | None, where_meta: dict | None):
    if source_system:
        stmt = stmt.where(Chunk.source_system == source_system)
    if where_meta:
        # JSONB containment (@>): doc_metadata @> '{"severity":"high"}'
        stmt = stmt.where(Chunk.doc_metadata.contains(where_meta))
    return stmt


async def _vector(session, q_emb, k, source_system, where_meta):
    stmt = _scoped(
        select(Chunk).order_by(Chunk.embedding.cosine_distance(q_emb)).limit(k),
        source_system,
        where_meta,
    )
    return list((await session.execute(stmt)).scalars().all())


async def _keyword(session, query, k, source_system, where_meta):
    tsq = func.plainto_tsquery("english", query)
    stmt = _scoped(
        select(Chunk)
        .where(Chunk.content_tsv.op("@@")(tsq))
        .order_by(func.ts_rank(Chunk.content_tsv, tsq).desc())
        .limit(k),
        source_system,
        where_meta,
    )
    return list((await session.execute(stmt)).scalars().all())


async def advanced_search(
    session: AsyncSession,
    query: str,
    k: int = 5,
    fetch_k: int = 20,
    source_system: str | None = None,
    where_meta: dict | None = None,
    use_hyde: bool = False,
    multi_query: bool = False,
    rerank: bool = True,
) -> list[Chunk]:
    """Hybrid retrieval with optional rewriting/HyDE/metadata-filter, fused +
    reranked. ``where_meta`` is a JSONB-containment filter, e.g.
    ``{"severity": "high"}``."""
    queries = await rewrite_query(query) if multi_query else [query]

    ranked: list[list[Chunk]] = []
    for q in queries:
        q_emb = await hyde_embedding(q) if use_hyde else (await embed_texts([q]))[0]
        vec, kw = await asyncio.gather(
            _vector(session, q_emb, fetch_k, source_system, where_meta),
            _keyword(session, q, fetch_k, source_system, where_meta),
            return_exceptions=True,
        )
        ranked.append(vec if isinstance(vec, list) else [])
        ranked.append(kw if isinstance(kw, list) else [])

    fused = rrf_merge(ranked, top_n=fetch_k)
    if rerank and fused:
        return await llm_rerank(query, fused, top_n=k)
    return fused[:k]
