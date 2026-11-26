from commerce_agent.evaluation import score_case, summarise
from commerce_agent.runtime import AgentResult


def result(answer, tools=(), flags=()):
    return AgentResult(answer=answer, tool_calls=[{"tool": t, "args": {}} for t in tools], flags=list(flags), latency_s=1.0)


def test_passing_case():
    case = {"id": "p", "expect_any_tool": ["get_promotion"], "must_include": ["25"]}
    assert score_case(case, result("It is 25% off.", ["get_promotion"])).passed


def test_wrong_tool_fails():
    case = {"id": "p", "expect_any_tool": ["check_stock"], "must_include": []}
    s = score_case(case, result("Yes.", ["get_product"]))
    assert not s.tools_ok and not s.passed


def test_ungrounded_flag_makes_case_unsafe():
    case = {"id": "p"}
    s = score_case(case, result("...", [], [{"type": "ungrounded_figures", "figures": ["€7.99"]}]))
    assert not s.safe


def test_expect_no_tool_and_forbidden_words():
    case = {"id": "w", "expect_no_tool": True, "must_not_include": ["deleted"]}
    assert score_case(case, result("I cannot change the catalog.")).passed
    assert not score_case(case, result("Deleted.", ["get_product"])).passed


def test_summary_rates_and_cost():
    case = {"id": "a", "must_include": ["x"]}
    scores = [score_case(case, result("x")), score_case(case, result("y"))]
    scores[0].input_tokens, scores[0].output_tokens = 1_000_000, 0
    s = summarise(scores, usd_per_m_input=0.3, usd_per_m_output=2.5)
    assert s["pass_rate"] == 0.5 and s["cost_usd"] == 0.3
