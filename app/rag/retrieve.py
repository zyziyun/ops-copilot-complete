from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import embed_texts
from app.models import Chunk


async def retrieve(session: AsyncSession, question: str, k: int = 5) -> list[Chunk]:
    q_emb = (await embed_texts([question]))[0]
    stmt = (
        select(Chunk)
        .order_by(Chunk.embedding.cosine_distance(q_emb))
        .limit(k)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
