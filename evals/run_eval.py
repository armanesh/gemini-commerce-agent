"""Run the evaluation set against Gemini and write results.

Usage:
  export GOOGLE_API_KEY=...            # or Vertex AI settings, see README
  python -m evals.run_eval [--model gemini-3.8-flash] [--usd-per-m-input X --usd-per-m-output Y]
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


async def ask_with_retry(service, question: str, retries: int):
    """Retry on rate limits (429) and temporary overload (503), with growing waits."""
    for attempt in range(retries + 1):
        try:
            return (await service.ask(question))[1]
        except Exception as e:
            text = str(e)
            transient = "429" in text or "503" in text or "RESOURCE_EXHAUSTED" in text or "UNAVAILABLE" in text
            if not transient or attempt == retries or "per day" in text:
                raise
            await asyncio.sleep(30 * (attempt + 1))


async def main(args) -> dict:
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    service = AgentService(build_agent(args.model))
    scores = []
    errors = []
    try:
        for case in cases:
            try:
                result = await ask_with_retry(service, case["question"], args.retries)
            except Exception as e:  # record the failure and keep going
                print(f"{case['id']:<20} ERROR {type(e).__name__}: {e}")
                errors.append({"id": case["id"], "error": f"{type(e).__name__}: {e}"[:500]})
                continue
            scores.append(score_case(case, result))
            print(f"{case['id']:<20} {'PASS' if scores[-1].passed else 'FAIL'}  {result.latency_s:.2f}s")
            await asyncio.sleep(args.pause)
    finally:
        await service.close()
    summary = summarise(scores, args.usd_per_m_input, args.usd_per_m_output)
    summary["model"] = args.model
    summary["errors"] = errors
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
    p.add_argument("--pause", type=float, default=15.0, help="seconds between cases, to stay under per-minute limits")
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--only", default=None, help="comma-separated case ids to run")
    a = p.parse_args()
    if a.model is None:
        from commerce_agent.agent import DEFAULT_MODEL
        a.model = DEFAULT_MODEL
    asyncio.run(main(a))
