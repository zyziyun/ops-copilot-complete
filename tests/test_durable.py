"""Same thread_id resumes from the checkpoint without re-running prior steps."""
import pytest
from langgraph.types import Command

from app.agent import tools as tools_mod
from app.agent.graph import build_graph
from tests.fakes import ScriptedChatModel, ai_text, ai_tool_call
from tests.helpers import requires_c3

pytestmark = requires_c3  # skip until C3's graph + tools are implemented


@pytest.mark.asyncio
async def test_resume_does_not_replay_prior_steps(memory_checkpointer, monkeypatch):
    async def fake_terminate(session, pid):
        return f"terminated pid {pid}"

    monkeypatch.setattr(tools_mod, "terminate_query", fake_terminate)

    model = ScriptedChatModel(
        responses=[
            ai_tool_call("terminate_query", {"pid": 8123}),
            ai_text("Done."),
        ]
    )
    saver = memory_checkpointer
    cfg = {"configurable": {"thread_id": "incident-42"}}

    agent1 = build_graph(saver, model=model)
    await agent1.ainvoke({"messages": [("user", "kill pid 8123")]}, cfg)
    snap = await agent1.aget_state(cfg)
    assert snap.next == ("approval",)  # paused at the gate
    assert model.call_count == 1  # only the first reasoning step ran

    # discard the graph object; rebuild from the same saver + thread_id
    del agent1
    agent2 = build_graph(saver, model=model)
    result = await agent2.ainvoke(Command(resume="approve"), cfg)

    # step 1 was NOT replayed: exactly one further model call (the final answer)
    assert model.call_count == 2
    assert "Done" in result["messages"][-1].content
