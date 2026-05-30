"""Environment probing + skip markers shared across tests.

Importing this (and conftest) guarantees the config env vars exist so app
modules import cleanly even with no real ``.env`` present.
"""
import os
import re
import socket

os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/app"
)
os.environ.setdefault("SEARCH_API_KEY", "tvly-test")

import pytest  # noqa: E402


def _db_reachable() -> bool:
    url = os.environ["DATABASE_URL"]
    m = re.search(r"@([^:/]+):(\d+)", url)
    host, port = (m.group(1), int(m.group(2))) if m else ("localhost", 5432)
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


DB_AVAILABLE = _db_reachable()
_key = os.environ.get("OPENAI_API_KEY", "")
OPENAI_AVAILABLE = _key.startswith("sk-") and _key != "sk-test"

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE, reason="Postgres not reachable on DATABASE_URL"
)
requires_openai = pytest.mark.skipif(
    not OPENAI_AVAILABLE, reason="no real OPENAI_API_KEY in env"
)


def _implemented(probe) -> bool:
    """True unless the probed function is still a `raise NotImplementedError` stub.

    Lets the *same* provided tests live in the starter and skip cleanly until the
    chapter that builds the code they exercise. In the complete repo every probe
    succeeds, so nothing skips.
    """
    try:
        probe()
        return True
    except NotImplementedError:
        return False


def _c2_probe():
    from app.rag.fusion import rrf_merge

    rrf_merge([])


def _c3_probe():
    from app.agent.graph import build_graph

    build_graph(None)


C2_BUILT = _implemented(_c2_probe)
C3_BUILT = _implemented(_c3_probe)

requires_c2 = pytest.mark.skipif(not C2_BUILT, reason="C2 not implemented yet")
requires_c3 = pytest.mark.skipif(not C3_BUILT, reason="C3 not implemented yet")
