"""Fixtures shared by the co-located unit tests under app/**/tests."""
import pytest
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture
def memory_checkpointer():
    """In-memory saver so HITL/durable/injection tests run with no Postgres.

    CI exercises the real AsyncPostgresSaver through the DB-backed tests; the
    safety invariants here are checkpointer-agnostic, so a MemorySaver keeps
    them fast and infra-free locally.
    """
    return MemorySaver()
