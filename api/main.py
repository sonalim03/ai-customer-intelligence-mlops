"""
FastAPI service wrapping the FinSight agent.

Endpoints:
POST /chat           — ask the agent a question
GET  /health         — liveness + whether the agent can be built
GET  /logs/summary   — aggregate stats from logged runs
GET  /               — basic API status message

The agent is built lazily on first request and cached.
FinSight uses Ollama + Llama 3.2 locally, so no paid API key is required.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException

from agent.graph import build_agent, ask_with_trace
from agent.observability import summarize_logs
from api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LogsSummaryResponse,
)


app = FastAPI(
    title="FinSight API",
    description=(
        "AI financial research agent — stock data, portfolio analysis, "
        "ML risk scoring, and financial news search behind one "
        "conversational endpoint."
    ),
    version="0.1.0",
)


_agent_cache = {
    "agent": None,
    "error": None,
}


def get_agent():
    """
    Build the agent once and cache it.

    Returns:
        (agent, error_message)
    """

    if _agent_cache["agent"] is not None:
        return _agent_cache["agent"], None

    if _agent_cache["error"] is not None:
        return None, _agent_cache["error"]

    try:
        _agent_cache["agent"] = build_agent()
        return _agent_cache["agent"], None

    except Exception as error:
        _agent_cache["error"] = str(error)
        return None, str(error)


@app.get("/health", response_model=HealthResponse)
def health():
    """
    Liveness check.

    The API itself remains available even if the local Ollama agent
    cannot currently be initialized.
    """

    agent, error = get_agent()

    return HealthResponse(
        status="ok",
        agent_ready=agent is not None,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a financial research question to FinSight.
    """

    agent, error = get_agent()

    if agent is None:
        raise HTTPException(
            status_code=503,
            detail=f"Agent not available: {error}",
        )

    try:
        result = ask_with_trace(
            agent,
            request.message,
            thread_id=request.thread_id,
        )

        return ChatResponse(
            response=result["response"],
            tools_called=result["tools_called"],
            blocked=result["blocked"],
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Agent request failed: {error}",
        )


@app.get(
    "/logs/summary",
    response_model=LogsSummaryResponse,
)
def logs_summary():
    """
    Return aggregate observability statistics.
    """

    return LogsSummaryResponse(
        **summarize_logs()
    )


@app.get("/")
def root():
    return {
        "message": (
            "FinSight API is running. "
            "Open /docs for the interactive API explorer."
        )
    }
