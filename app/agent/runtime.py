"""Durable agent runtime: a process-wide agent backed by a persistent psycopg
connection pool to the same Postgres, so runs survive restarts by thread_id."""
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.agent.graph import build_graph
from app.config import settings

# psycopg-style URL for the checkpointer (plain postgresql://, no +asyncpg)
CKPT_URL = settings.checkpoint_url

_CONNECTION_KWARGS = {"autocommit": True, "prepare_threshold": 0}

_pool: AsyncConnectionPool | None = None
_agent = None


async def get_agent():
    global _pool, _agent
    if _agent is None:
        _pool = AsyncConnectionPool(
            conninfo=CKPT_URL,
            max_size=settings.pool_size,
            open=False,
            kwargs=_CONNECTION_KWARGS,
        )
        # wait=True so connections exist before setup() uses one; without it
        # psycopg-pool 3.3+ returns early and setup() hangs
        await _pool.open(wait=True, timeout=10)
        saver = AsyncPostgresSaver(_pool)
        await saver.setup()
        _agent = build_graph(saver)
    return _agent


async def close_agent() -> None:
    global _pool, _agent
    if _pool is not None:
        await _pool.close()
    _pool = None
    _agent = None
