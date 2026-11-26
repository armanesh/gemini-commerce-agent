"""End to end: real ADK runner, real MCP server over stdio, real guardrails, scripted model."""

import asyncio

from commerce_agent.agent import build_agent
from commerce_agent.runtime import AgentService
from scripted_llm import ScriptedLlm, call, say


def run(turns, question="question"):
    async def go():
        svc = AgentService(build_agent(ScriptedLlm(model="scripted", turns=turns)))
        try:
            return (await svc.ask(question))[1]
        finally:
            await svc.close()

    return asyncio.run(asyncio.wait_for(go(), 60))


def test_grounded_answer_with_two_tool_calls():
    r = run([call("get_product", sku="SKN-102"), call("get_promotion", sku="SKN-102"),
             say("The Gentle Foaming Cleanser costs €8.49 and is 25% off, so €6.37.")])
    assert [c["tool"] for c in r.tool_calls] == ["get_product", "get_promotion"]
    assert "€6.37" in r.answer
    assert r.flags == []


def test_invented_price_is_replaced_and_flagged():
    from commerce_agent.guardrails import FALLBACK_ANSWER

    r = run([call("get_product", sku="SKN-102"), say("It costs €7.99.")])
    assert r.answer == FALLBACK_ANSWER
    assert r.flags[0] == {"type": "ungrounded_figures", "figures": ["€7.99"]}


def test_disallowed_tool_never_runs():
    r = run([call("delete_product", sku="SKN-102"), say("I cannot do that.")])
    assert r.flags[0]["type"] == "blocked_tool_call"
    assert r.answer == "I cannot do that."


def test_malformed_sku_is_blocked_before_the_tool():
    r = run([call("check_stock", sku="skn101"), say("Please give a product code like SKN-101.")])
    assert r.flags[0]["reason"].startswith("'skn101' is not a valid SKU")
