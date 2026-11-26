"""Guardrails around the agent.

1. Tool allowlist and argument checks before any tool runs (least privilege).
2. Grounding check on the final answer: every price or percentage the agent
   states must come from a tool result in this session, or be a discount
   computed from one. Otherwise the answer is replaced and the event is flagged.
"""

from __future__ import annotations

import json
import re
from typing import Any

from commerce_agent.catalog import SKU_PATTERN

ALLOWED_TOOLS = frozenset({"search_products", "get_product", "check_stock", "get_promotion"})
GROUNDED_KEY = "grounded_numbers"
FLAG_KEY = "guardrail_flags"

FALLBACK_ANSWER = (
    "I could not confirm all the figures in my answer against the catalog, so I will not state them. "
    "Please check the product page or ask a colleague in store."
)

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_MONEY = re.compile(r"(?:€|eur(?:o|os)?)\s*(\d+(?:[.,]\d{1,2})?)|(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur(?:o|os)?)\b", re.I)
_PERCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|percent)", re.I)


def _to_float(s: str) -> float:
    return round(float(s.replace(",", ".")), 2)


def check_tool_call(tool_name: str, args: dict[str, Any]) -> str | None:
    """Return an error message if the call is not allowed, else None."""
    if tool_name not in ALLOWED_TOOLS:
        return f"Tool '{tool_name}' is not allowed for this agent."
    sku = args.get("sku")
    if sku is not None and not SKU_PATTERN.match(str(sku).strip().upper()):
        return f"'{sku}' is not a valid SKU (expected format ABC-123)."
    return None


def numbers_in(obj: Any) -> set[float]:
    """All numbers that appear anywhere in a tool result."""
    text = obj if isinstance(obj, str) else json.dumps(obj, default=str)
    return {_to_float(n) for n in _NUMBER.findall(text)}


def allowed_figures(grounded: set[float]) -> set[float]:
    """Grounded numbers plus prices after a grounded percentage discount."""
    allowed = set(grounded)
    pcts = [g for g in grounded if 0 < g < 100]
    for price in grounded:
        for p in pcts:
            allowed.add(round(price * (1 - p / 100), 2))
    return allowed


def ungrounded_figures(answer: str, grounded: set[float]) -> list[str]:
    """Money amounts and percentages in the answer that no tool returned."""
    allowed = allowed_figures(grounded)
    bad = []
    for m in _MONEY.finditer(answer):
        value = m.group(1) or m.group(2)
        if _to_float(value) not in allowed:
            bad.append(m.group(0).strip())
    for m in _PERCENT.finditer(answer):
        if _to_float(m.group(1)) not in grounded:
            bad.append(m.group(0).strip())
    return bad


# ---- ADK callbacks -------------------------------------------------------

def before_tool(tool, args, tool_context):
    error = check_tool_call(tool.name, args)
    if error:
        flags = list(tool_context.state.get(FLAG_KEY, []))
        flags.append({"type": "blocked_tool_call", "tool": tool.name, "reason": error})
        tool_context.state[FLAG_KEY] = flags
        return {"error": error}
    return None


def after_tool(tool, args, tool_context, tool_response):
    grounded = set(tool_context.state.get(GROUNDED_KEY, []))
    grounded |= numbers_in(tool_response)
    tool_context.state[GROUNDED_KEY] = sorted(grounded)
    return None


def after_model(callback_context, llm_response):
    content = llm_response.content
    if not content or not content.parts or llm_response.partial:
        return None
    if any(getattr(p, "function_call", None) for p in content.parts):
        return None
    text = "".join(p.text or "" for p in content.parts if getattr(p, "text", None))
    if not text:
        return None
    grounded = set(callback_context.state.get(GROUNDED_KEY, []))
    bad = ungrounded_figures(text, grounded)
    if not bad:
        return None
    flags = list(callback_context.state.get(FLAG_KEY, []))
    flags.append({"type": "ungrounded_figures", "figures": bad})
    callback_context.state[FLAG_KEY] = flags
    from google.genai import types

    return llm_response.model_copy(
        update={"content": types.Content(role="model", parts=[types.Part(text=FALLBACK_ANSWER)])}
    )
