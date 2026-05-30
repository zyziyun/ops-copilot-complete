import pytest
from sqlalchemy import delete

from app.db import SessionLocal
from app.models import Chunk
from app.rag.keyword import keyword_search
from app.testing import requires_c2, requires_db

pytestmark = [requires_c2, requires_db]  # needs C2's keyword_search + a Postgres


@pytest.mark.asyncio
async def test_keyword_finds_exact_token():
    """Keyword arm nails an exact identifier dense retrieval would miss."""
    async with SessionLocal() as s:
        await s.execute(delete(Chunk).where(Chunk.source == "_kwtest"))
        s.add(
            Chunk(
                source="_kwtest",
                chunk_index=0,
                content="To configure pg_hba.conf authentication add a host line.",
                embedding=[0.0] * 1536,
                source_system="postgres",
            )
        )
        await s.commit()
        rows = await keyword_search(s, "pg_hba.conf authentication", k=5)
        assert any(c.source == "_kwtest" for c in rows)
        await s.execute(delete(Chunk).where(Chunk.source == "_kwtest"))
        await s.commit()
