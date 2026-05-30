"""Global pytest setup, applied to every test (co-located unit tests under
``app/**/tests`` and the e2e tests under ``tests/e2e``).

Two jobs:
1. Provide config env defaults so app modules import without a real ``.env``.
2. Rebind the SQLAlchemy engine to ``NullPool`` for tests — pytest-asyncio runs
   each test in its own event loop, and a pooled async engine caches connections
   to the loop that opened them, so the 2nd DB test would fail with "Event loop
   is closed". The app keeps its real pool; this is test-only wiring.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/app"
)
os.environ.setdefault("SEARCH_API_KEY", "tvly-test")

from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

import app.db as appdb  # noqa: E402

_test_engine = create_async_engine(appdb.settings.database_url, poolclass=NullPool)
appdb.engine = _test_engine
appdb.SessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)
