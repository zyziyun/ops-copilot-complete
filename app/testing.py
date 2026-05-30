"""Shared test support: environment probes, skip markers, and a scripted fake
chat model. Imported by the co-located unit tests and the e2e suite alike.

This module is excluded from the Docker image (see .dockerignore); it lives under
``app/`` only so tests can import it with a stable ``app.testing`` path.
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
from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402
from pydantic import PrivateAttr  # noqa: E402


# --------------------------------------------------------------------------- #
# Environment probes + skip markers
# --------------------------------------------------------------------------- #
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
    """True unless the probed function is still a ``raise NotImplementedError`` stub.

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


# --------------------------------------------------------------------------- #
# Scripted, deterministic chat model so agent tests never hit OpenAI
# --------------------------------------------------------------------------- #
class ScriptedChatModel(BaseChatModel):
    """Returns a pre-baked sequence of AIMessages (each optionally carrying
    tool_calls), letting tests drive the exact ReAct path they want to assert
    on. ``bind_tools`` is a no-op returning ``self`` so it drops into
    ``build_graph`` in place of ChatOpenAI."""

    responses: list
    _i: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        idx = min(self._i, len(self.responses) - 1)
        msg = self.responses[idx]
        self._i += 1
        return ChatResult(generations=[ChatGeneration(message=msg)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    @property
    def call_count(self) -> int:
        return self._i


def ai_tool_call(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


def ai_text(text: str) -> AIMessage:
    return AIMessage(content=text)
