from fastapi.testclient import TestClient

from api.main import create_app
from commerce_agent.agent import build_agent
from scripted_llm import ScriptedLlm, call, say


def test_chat_endpoint_returns_answer_trace_and_flags():
    model = ScriptedLlm(model="scripted", turns=[call("search_products", query="vegan gluten free", category="snacks"),
                                                  say("Try the Sea Salt Lentil Crisps at €2.19.")])
    with TestClient(create_app(build_agent(model))) as client:
        r = client.post("/api/chat", json={"question": "vegan snacks?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Try the Sea Salt Lentil Crisps at €2.19."
    assert body["tool_calls"][0]["tool"] == "search_products"
    assert body["flags"] == []


def test_empty_question_is_rejected():
    model = ScriptedLlm(model="scripted", turns=[say("hi")])
    with TestClient(create_app(build_agent(model))) as client:
        assert client.post("/api/chat", json={"question": ""}).status_code == 422
