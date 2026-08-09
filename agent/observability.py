"""
Structured logging for every agent run — the observability layer.

Every call to ask()/ask_with_trace() writes one JSON line to
logs/agent_runs.jsonl with: timestamp, thread_id, the (PII-redacted)
query, whether it was blocked by guardrails, which tools were called,
latency, and a preview of the response.

Why JSON lines and not a real observability platform (LangSmith/Phoenix)?
This is dependency-free and gives you something to build a dashboard on
top of in Step 6 without needing another account/service. Swapping in
LangSmith later is a good documented "v2" — mention it in your README.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

from agent.guardrails import redact_pii

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_PATH = LOG_DIR / "agent_runs.jsonl"


def log_run(
    thread_id: str,
    query: str,
    blocked: bool,
    block_reason: str | None,
    tools_called: list,
    latency_s: float,
    response_preview: str,
) -> None:
    LOG_DIR.mkdir(exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": thread_id,
        "query": redact_pii(query),
        "blocked": blocked,
        "block_reason": block_reason,
        "tools_called": tools_called,
        "latency_s": round(latency_s, 3),
        "response_preview": redact_pii(response_preview[:200]),
    }

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_recent_runs(n: int = 20) -> list:
    """Read the last n log entries — used by the dashboard in Step 6."""
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH) as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-n:]]


def summarize_logs() -> dict:
    """Quick aggregate stats over all logged runs — also for Step 6's dashboard."""
    if not LOG_PATH.exists():
        return {"total_runs": 0}

    with open(LOG_PATH) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    if not entries:
        return {"total_runs": 0}

    blocked_count = sum(1 for e in entries if e["blocked"])
    latencies = [e["latency_s"] for e in entries if not e["blocked"]]
    avg_latency = round(sum(latencies) / len(latencies), 3) if latencies else None

    tool_counts = {}
    for e in entries:
        for t in e.get("tools_called", []):
            tool_counts[t] = tool_counts.get(t, 0) + 1

    return {
        "total_runs": len(entries),
        "blocked_runs": blocked_count,
        "block_rate": round(blocked_count / len(entries), 3),
        "avg_latency_s": avg_latency,
        "tool_usage_counts": tool_counts,
    }
