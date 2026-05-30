import pytest
from sqlalchemy import text

from app.agent.tools import create_ticket, get_db_connections
from app.db import SessionLocal
from app.testing import requires_c3, requires_db

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
