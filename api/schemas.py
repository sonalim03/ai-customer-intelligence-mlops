"""
Request/response schemas for the FinSight API.
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000,
                          description="The user's financial research question.")
    thread_id: str = Field(default="default",
                            description="Conversation thread ID for multi-turn memory.")


class ChatResponse(BaseModel):
    response: str
    tools_called: list[str]
    blocked: bool


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool


class LogsSummaryResponse(BaseModel):
    total_runs: int
    blocked_runs: int | None = None
    block_rate: float | None = None
    avg_latency_s: float | None = None
    tool_usage_counts: dict | None = None
