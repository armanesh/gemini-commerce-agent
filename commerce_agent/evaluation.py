"""Scoring for the evaluation set. Kept free of model calls so it is unit-tested."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CaseScore:
    id: str
    passed: bool
    tools_ok: bool
    facts_ok: bool
    safe: bool
    latency_s: float
    input_tokens: int
    output_tokens: int
    answer: str
    notes: list[str]


def score_case(case: dict[str, Any], result) -> CaseScore:
    answer = result.answer.lower()
    called = {c["tool"] for c in result.tool_calls}
    notes = []

    expected_tools = set(case.get("expect_any_tool", []))
    tools_ok = not expected_tools or bool(called & expected_tools)
    if not tools_ok:
        notes.append(f"expected one of {sorted(expected_tools)}, called {sorted(called)}")
    if case.get("expect_no_tool") and called:
        tools_ok = False
        notes.append(f"expected no tool call, called {sorted(called)}")

    facts_ok = all(s.lower() in answer for s in case.get("must_include", []))
    for group in case.get("must_include_any", []):
        if not any(s.lower() in answer for s in group):
            facts_ok = False
            notes.append(f"missing any of {group}")
    if not facts_ok and case.get("must_include"):
        notes.append(f"must include {case['must_include']}")

    bad = [s for s in case.get("must_not_include", []) if s.lower() in answer]
    ungrounded = [f for f in result.flags if f["type"] == "ungrounded_figures"]
    safe = not bad and not ungrounded
    if bad:
        notes.append(f"contains {bad}")
    if ungrounded:
        notes.append("guardrail replaced an ungrounded answer")

    return CaseScore(case["id"], tools_ok and facts_ok and safe, tools_ok, facts_ok, safe,
                     result.latency_s, result.input_tokens, result.output_tokens, result.answer, notes)


def summarise(scores: list[CaseScore], usd_per_m_input: float | None = None, usd_per_m_output: float | None = None) -> dict[str, Any]:
    n = len(scores) or 1
    lat = sorted(s.latency_s for s in scores) or [0.0]
    summary = {
        "cases": len(scores),
        "pass_rate": round(sum(s.passed for s in scores) / n, 3),
        "tool_selection": round(sum(s.tools_ok for s in scores) / n, 3),
        "factual": round(sum(s.facts_ok for s in scores) / n, 3),
        "safe": round(sum(s.safe for s in scores) / n, 3),
        "latency_p50_s": lat[len(lat) // 2],
        "latency_max_s": lat[-1],
        "input_tokens": sum(s.input_tokens for s in scores),
        "output_tokens": sum(s.output_tokens for s in scores),
    }
    if usd_per_m_input is not None and usd_per_m_output is not None:
        summary["cost_usd"] = round(summary["input_tokens"] / 1e6 * usd_per_m_input
                                    + summary["output_tokens"] / 1e6 * usd_per_m_output, 4)
    summary["results"] = [asdict(s) for s in scores]
    return summary
