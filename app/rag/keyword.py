from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk


async def keyword_search(
    session: AsyncSession, query: str, k: int = 20
) -> list[Chunk]:
    tsq = func.plainto_tsquery("english", query)
    stmt = (
        select(Chunk)
        .where(Chunk.content_tsv.op("@@")(tsq))
        .order_by(func.ts_rank(Chunk.content_tsv, tsq).desc())
        .limit(k)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
