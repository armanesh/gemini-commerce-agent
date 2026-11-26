"""A scripted model for offline tests: plays back fixed turns instead of calling Gemini.

It lets the tests run the real ADK runner, the real MCP server and the real
guardrails without an API key.
"""

from __future__ import annotations

from typing import AsyncGenerator

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.models.llm_response import LlmResponse as _R  # noqa: F401
from google.genai import types


class ScriptedLlm(BaseLlm):
    turns: list[types.Content]
    calls: int = 0

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        turn = self.turns[min(self.calls, len(self.turns) - 1)]
        self.calls += 1
        yield LlmResponse(content=turn, turn_complete=True)


def call(name: str, **args) -> types.Content:
    return types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))])


def say(text: str) -> types.Content:
    return types.Content(role="model", parts=[types.Part(text=text)])
