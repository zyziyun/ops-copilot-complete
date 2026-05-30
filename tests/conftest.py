import tests.helpers  # noqa: F401  ensures env defaults are set before app import

import pytest
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# pytest-asyncio runs each test in its own event loop, but a pooled async engine
# caches connections bound to the loop that first opened them, so the second DB
# test fails with "Event loop is closed". Rebinding the engine to NullPool (a
# fresh connection per session, closed on exit) sidesteps that entirely. This is
# test-only wiring; the app keeps its real connection pool.
import app.db as appdb  # noqa: E402

_test_engine = create_async_engine(appdb.settings.database_url, poolclass=NullPool)
appdb.engine = _test_engine
appdb.SessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest.fixture
def memory_checkpointer():
    """In-memory saver so HITL/durable/injection tests run with no Postgres.

    CI exercises the real AsyncPostgresSaver through the DB-backed tests; the
    safety invariants here are checkpointer-agnostic, so a MemorySaver keeps
    them fast and infra-free locally.
    """
    return MemorySaver()
