"""Run the evaluation set against Gemini and write results.

Usage:
  export GOOGLE_API_KEY=...            # or Vertex AI settings, see README
  python -m evals.run_eval [--model gemini-2.5-flash] [--usd-per-m-input X --usd-per-m-output Y]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from commerce_agent.agent import build_agent
from commerce_agent.evaluation import score_case, summarise
from commerce_agent.runtime import AgentService

HERE = Path(__file__).resolve().parent


async def main(args) -> dict:
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    service = AgentService(build_agent(args.model))
    scores = []
    try:
        for case in cases:
            _, result = await service.ask(case["question"])
            scores.append(score_case(case, result))
            print(f"{case['id']:<20} {'PASS' if scores[-1].passed else 'FAIL'}  {result.latency_s:.2f}s")
    finally:
        await service.close()
    summary = summarise(scores, args.usd_per_m_input, args.usd_per_m_output)
    summary["model"] = args.model
    out = HERE / "results" / f"{time.strftime('%Y%m%d-%H%M%S')}_{args.model}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print({k: v for k, v in summary.items() if k != "results"})
    print(f"written to {out}")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=None)
    p.add_argument("--usd-per-m-input", type=float, default=None)
    p.add_argument("--usd-per-m-output", type=float, default=None)
    a = p.parse_args()
    if a.model is None:
        from commerce_agent.agent import DEFAULT_MODEL
        a.model = DEFAULT_MODEL
    asyncio.run(main(a))
