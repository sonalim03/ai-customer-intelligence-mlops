"""
Run the golden query set against the live agent and score the results.

This is the script that gets wired into CI (Step 7) — a regression in
tool-calling accuracy or groundedness should fail the build, the same
way a broken unit test would.

Usage:
    python evals/run_evals.py                  # run full suite, print report
    python evals/run_evals.py --threshold 0.7   # fail (exit 1) if avg F1 < 0.7
"""
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import AIMessage, ToolMessage

from agent.graph import build_agent
from evals.golden_queries import GOLDEN_QUERIES
from evals.scorer import score_tool_calls, score_groundedness

RESULTS_PATH = Path(__file__).parent / "results.json"


def run_single_query(agent, case: dict) -> dict:
    start = time.perf_counter()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": case["query"]}]},
        config={"configurable": {"thread_id": f"eval-{case['id']}"}},
    )
    latency_s = round(time.perf_counter() - start, 2)

    messages = result["messages"]
    final_answer = messages[-1].content

    actual_tools = []
    tool_outputs = []
    for m in messages:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            actual_tools.extend(tc["name"] for tc in m.tool_calls)
        if isinstance(m, ToolMessage):
            tool_outputs.append(str(m.content))

    tool_score = score_tool_calls(case["expected_tools"], actual_tools)
    ground_score = score_groundedness(final_answer, " ".join(tool_outputs))

    return {
        "id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "expected_tools": case["expected_tools"],
        "actual_tools": actual_tools,
        "final_answer": final_answer,
        "latency_s": latency_s,
        "tool_score": tool_score,
        "groundedness": ground_score,
    }


def summarize(results: list) -> dict:
    n = len(results)
    avg_f1 = round(sum(r["tool_score"]["f1"] for r in results) / n, 3)
    exact_match_rate = round(
        sum(1 for r in results if r["tool_score"]["exact_match"]) / n, 3
    )
    grounded = [r["groundedness"]["grounded_ratio"] for r in results
                if r["groundedness"]["grounded_ratio"] is not None]
    avg_groundedness = round(sum(grounded) / len(grounded), 3) if grounded else None
    avg_latency = round(sum(r["latency_s"] for r in results) / n, 2)
    p95_latency = round(sorted(r["latency_s"] for r in results)[int(n * 0.95) - 1], 2) if n > 1 else results[0]["latency_s"]

    return {
        "n_cases": n,
        "avg_tool_call_f1": avg_f1,
        "exact_match_rate": exact_match_rate,
        "avg_groundedness": avg_groundedness,
        "avg_latency_s": avg_latency,
        "p95_latency_s": p95_latency,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.7,
                         help="Minimum avg tool-call F1 to pass (exit 0). Default 0.7")
    args = parser.parse_args()

    print(f"Running {len(GOLDEN_QUERIES)} eval cases...\n")
    try:
        agent = build_agent()
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    results = []
    for case in GOLDEN_QUERIES:
        print(f"  [{case['id']}] {case['query'][:60]}...")
        r = run_single_query(agent, case)
        results.append(r)
        status = "✅" if r["tool_score"]["exact_match"] else "⚠️"
        print(f"    {status} expected={r['expected_tools']} actual={r['actual_tools']} "
              f"f1={r['tool_score']['f1']} latency={r['latency_s']}s")

    summary = summarize(results)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for k, v in summary.items():
        print(f"  {k}: {v}")

    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nFull results saved to {RESULTS_PATH}")

    if summary["avg_tool_call_f1"] < args.threshold:
        print(f"\n❌ FAILED: avg tool-call F1 {summary['avg_tool_call_f1']} "
              f"< threshold {args.threshold}")
        sys.exit(1)
    print(f"\n✅ PASSED: avg tool-call F1 {summary['avg_tool_call_f1']} "
          f">= threshold {args.threshold}")


if __name__ == "__main__":
    main()
