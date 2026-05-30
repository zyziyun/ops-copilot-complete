import pytest
from sqlalchemy import delete, text

from app.agent.tools import create_ticket, get_db_connections
from app.db import SessionLocal
from app.models import Chunk
from app.rag.keyword import keyword_search
from tests.helpers import requires_c3, requires_db

pytestmark = requires_c3  # tool bodies land in C3


@requires_db
@pytest.mark.asyncio
async def test_create_ticket_inserts_row():
    async with SessionLocal() as s:
        before = (await s.execute(text("SELECT count(*) FROM tickets"))).scalar()
        msg = await create_ticket(s, "connections near max", "high")
        assert msg.startswith("created ticket #")
        after = (await s.execute(text("SELECT count(*) FROM tickets"))).scalar()
        assert after == before + 1


@requires_db
@pytest.mark.asyncio
async def test_get_db_connections_format():
    async with SessionLocal() as s:
        out = await get_db_connections(s)
        assert out.startswith("connections: ")
        used, mx = out.removeprefix("connections: ").split("/")
        assert used.isdigit() and mx.isdigit()


@requires_db
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
