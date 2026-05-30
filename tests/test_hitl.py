"""The most important test: a write action never runs without human approval."""
import pytest
from langgraph.types import Command

from app.agent import tools as tools_mod
from app.agent.graph import build_graph
from tests.fakes import ScriptedChatModel, ai_text, ai_tool_call
from tests.helpers import requires_c3

pytestmark = requires_c3  # skip until C3's graph + tools are implemented


@pytest.fixture
def recorded_terminate(monkeypatch):
    calls = {"n": 0}

    async def fake_terminate(session, pid):
        calls["n"] += 1
        return f"terminated pid {pid}"

    monkeypatch.setattr(tools_mod, "terminate_query", fake_terminate)
    return calls


@pytest.mark.asyncio
async def test_write_pauses_for_approval_then_executes(
    memory_checkpointer, recorded_terminate
):
    model = ScriptedChatModel(
        responses=[
            ai_tool_call("terminate_query", {"pid": 999}),
            ai_text("Done. Terminated the stuck query."),
        ]
    )
    agent = build_graph(memory_checkpointer, model=model)
    cfg = {"configurable": {"thread_id": "t-hitl"}}

    await agent.ainvoke(
        {"messages": [("user", "terminate the stuck query on pid 999")]}, cfg
    )
    snap = await agent.aget_state(cfg)
    assert snap.next == ("approval",)  # paused at the gate, before tools
    assert snap.tasks[0].interrupts  # an approval request is pending
    assert recorded_terminate["n"] == 0  # write tool NOT executed

    result = await agent.ainvoke(Command(resume="approve"), cfg)
    assert recorded_terminate["n"] == 1  # executed only after approval
    assert "Done" in result["messages"][-1].content


@pytest.mark.asyncio
async def test_denied_write_never_executes(memory_checkpointer, recorded_terminate):
    model = ScriptedChatModel(
        responses=[
            ai_tool_call("terminate_query", {"pid": 999}),
            ai_text("Understood, I will not terminate it."),
        ]
    )
    agent = build_graph(memory_checkpointer, model=model)
    cfg = {"configurable": {"thread_id": "t-hitl-deny"}}

    await agent.ainvoke(
        {"messages": [("user", "terminate the stuck query on pid 999")]}, cfg
    )
    snap = await agent.aget_state(cfg)
    assert snap.next == ("approval",)

    await agent.ainvoke(Command(resume="deny"), cfg)
    assert recorded_terminate["n"] == 0  # denial means it never runs
