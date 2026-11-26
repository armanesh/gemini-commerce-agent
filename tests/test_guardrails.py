from types import SimpleNamespace

from commerce_agent import guardrails as g


def test_tool_allowlist():
    assert g.check_tool_call("get_product", {"sku": "SKN-101"}) is None
    assert "not allowed" in g.check_tool_call("delete_product", {"sku": "SKN-101"})


def test_sku_format_checked_before_tool_runs():
    assert "not a valid SKU" in g.check_tool_call("check_stock", {"sku": "skn101"})


def test_numbers_extracted_from_tool_result():
    assert g.numbers_in({"price_eur": 8.49, "value": 25}) >= {8.49, 25.0}


def test_grounded_answer_passes():
    grounded = {8.49, 25.0}
    assert g.ungrounded_figures("The cleanser costs €8.49 and is 25% off.", grounded) == []


def test_discounted_price_is_allowed():
    # 8.49 with 25 percent off is 6.37
    assert g.ungrounded_figures("With the promotion you pay €6.37.", {8.49, 25.0}) == []


def test_invented_price_and_percentage_are_caught():
    bad = g.ungrounded_figures("It costs 7,99 euro and is 30% off.", {8.49, 25.0})
    assert bad == ["7,99 euro", "30%"]


def test_answer_without_figures_passes():
    assert g.ungrounded_figures("It is in stock in Utrecht.", set()) == []


def test_before_tool_callback_blocks_and_flags():
    ctx = SimpleNamespace(state={})
    out = g.before_tool(SimpleNamespace(name="drop_table"), {}, ctx)
    assert "error" in out
    assert ctx.state[g.FLAG_KEY][0]["type"] == "blocked_tool_call"


def test_after_tool_callback_accumulates_grounded_numbers():
    ctx = SimpleNamespace(state={})
    g.after_tool(SimpleNamespace(name="get_product"), {}, ctx, {"price_eur": 12.99})
    g.after_tool(SimpleNamespace(name="get_promotion"), {}, ctx, {"value": 10})
    assert {12.99, 10.0} <= set(ctx.state[g.GROUNDED_KEY])
