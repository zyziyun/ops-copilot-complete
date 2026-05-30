"""A scripted, deterministic chat model so agent tests never hit OpenAI.

It returns a pre-baked sequence of ``AIMessage``s (each optionally carrying
tool_calls), letting tests drive the exact ReAct path they want to assert on.
``bind_tools`` is a no-op that returns ``self`` so it drops into ``build_graph``
in place of ``ChatOpenAI``.
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr


class ScriptedChatModel(BaseChatModel):
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
