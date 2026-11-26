"""Run the agent for one question and return the answer, tool trace and flags.

Shared by the API and the evaluation script.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from commerce_agent import guardrails

APP_NAME = "commerce_agent"


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    flags: list[dict[str, Any]] = field(default_factory=list)
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


class AgentService:
    def __init__(self, agent):
        self.sessions = InMemorySessionService()
        self.runner = Runner(app_name=APP_NAME, agent=agent, session_service=self.sessions)

    async def ask(self, question: str, user_id: str = "user", session_id: str | None = None) -> tuple[str, AgentResult]:
        session_id = session_id or uuid.uuid4().hex
        if await self.sessions.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id) is None:
            await self.sessions.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        message = types.Content(role="user", parts=[types.Part(text=question)])
        result = AgentResult(answer="")
        start = time.perf_counter()
        async for event in self.runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
            usage = getattr(event, "usage_metadata", None)
            if usage:
                result.input_tokens += usage.prompt_token_count or 0
                result.output_tokens += usage.candidates_token_count or 0
            if not event.content or not event.content.parts:
                continue
            for part in event.content.parts:
                if part.function_call:
                    result.tool_calls.append({"tool": part.function_call.name, "args": dict(part.function_call.args or {})})
            if event.is_final_response():
                result.answer = "".join(p.text or "" for p in event.content.parts if p.text)
        result.latency_s = round(time.perf_counter() - start, 3)
        session = await self.sessions.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        result.flags = list(session.state.get(guardrails.FLAG_KEY, [])) if session else []
        return session_id, result

    async def close(self):
        await self.runner.close()
