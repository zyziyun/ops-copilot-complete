"""Durable agent runtime backed by the same Postgres as the data layer.

NOTE on the checkpointer wiring: ``AsyncPostgresSaver.from_conn_string(url)``
returns an async *context manager*, so the connection it opens would be closed
as soon as the ``with`` block exits — useless for a long-lived web process.
Instead we open one persistent ``AsyncConnectionPool`` at startup and hand it to
the saver. psycopg needs ``autocommit=True`` and ``prepare_threshold=0`` for the
checkpointer's statements to work.
"""
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
    """Return a process-wide singleton agent compiled with the Postgres saver.

    Every run is keyed by a ``thread_id``; the same id resumes the same
    conversation from its last checkpoint, even in a fresh process.
    """
    global _pool, _agent
    if _agent is None:
        _pool = AsyncConnectionPool(
            conninfo=CKPT_URL,
            max_size=settings.pool_size,
            open=False,
            kwargs=_CONNECTION_KWARGS,
        )
        # wait=True so the pool establishes its connections before setup() uses
        # one — without it, psycopg-pool 3.3+ returns early and setup() hangs
        await _pool.open(wait=True, timeout=10)
        saver = AsyncPostgresSaver(_pool)
        await saver.setup()  # creates checkpoint tables once
        _agent = build_graph(saver)
    return _agent


async def close_agent() -> None:
    global _pool, _agent
    if _pool is not None:
        await _pool.close()
    _pool = None
    _agent = None
