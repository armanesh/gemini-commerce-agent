"""FastAPI backend for the web UI: one chat endpoint that returns the answer,
the tool calls the agent made and any guardrail flags."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from commerce_agent.runtime import AgentService

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tool_calls: list[dict]
    flags: list[dict]
    latency_s: float


def create_app(agent=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if agent is None:
            from commerce_agent.agent import root_agent as default_agent
            app.state.service = AgentService(default_agent)
        else:
            app.state.service = AgentService(agent)
        yield
        await app.state.service.close()

    app = FastAPI(title="Commerce assistant", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        session_id, result = await app.state.service.ask(req.question, session_id=req.session_id)
        return ChatResponse(session_id=session_id, answer=result.answer, tool_calls=result.tool_calls,
                            flags=result.flags, latency_s=result.latency_s)

    if WEB_DIST.exists():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    return app


app = create_app()
