import os
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from agent.tool_registry import ALL_TOOLS
from agent.guardrails import validate_input
from agent.observability import log_run


SYSTEM_PROMPT = """
You are FinSight, a financial research assistant for a retail investor.

You have access to tools for:
- stock data
- portfolio analysis
- ML-based risk prediction
- financial news search

Rules:
- Only state numbers that came from a tool call.
- Never invent prices, percentages, or risk labels.
- If a tool returns an error, tell the user plainly rather than guessing.
- When asked about portfolio risk or exposure, call analyze_portfolio.
- When asked about a specific stock's risk, call predict_risk_score.
- Mention that risk output is model-generated with a confidence score
  and is not financial advice.
- Keep answers concise and grounded in tool outputs.
- Do not tell the user to buy or sell anything.
- For general educational questions that do not require current or stored
  financial data, answer directly without calling a tool.
"""


def _build_llm(provider: str):
    """
    Construct the chat model for the given provider. Split out from
    build_agent() specifically so it's unit-testable without needing a
    live Ollama server or real AWS credentials — agent/test_provider.py
    monkeypatches the actual client classes and verifies the right one
    gets constructed with the right arguments.

    Providers:
      "ollama"  — local, free, used for development (default)
      "bedrock" — AWS-hosted, used for the Step 8 cloud deployment.
                  No API key needed — auth goes through the ECS task's
                  IAM role via boto3's default credential chain.
    """
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            temperature=0,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    if provider == "bedrock":
        from langchain_aws import ChatBedrockConverse
        return ChatBedrockConverse(
            model=os.getenv(
                "BEDROCK_MODEL_ID",
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
            ),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            temperature=0,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider!r}. Expected 'ollama' or 'bedrock'."
    )


def build_agent():
    """
    Build the FinSight agent. Which model backend it uses is controlled
    by the LLM_PROVIDER env var (defaults to "ollama" for local dev).
    Set LLM_PROVIDER=bedrock in the ECS task definition for the AWS
    deployment — see infra/README.md.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama")
    llm = _build_llm(provider)

    checkpointer = MemorySaver()

    return create_react_agent(
        llm,
        tools=ALL_TOOLS,
        state_modifier=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def ask(agent, message: str, thread_id: str = "default") -> str:
    is_valid, reason = validate_input(message)

    if not is_valid:
        blocked_response = f"I can't process that message: {reason}"

        log_run(
            thread_id=thread_id,
            query=message,
            blocked=True,
            block_reason=reason,
            tools_called=[],
            latency_s=0.0,
            response_preview=blocked_response,
        )

        return blocked_response

    start = time.perf_counter()

    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
    )

    latency_s = time.perf_counter() - start
    response = result["messages"][-1].content

    tools_called = [
        call["name"]
        for msg in result["messages"]
        for call in (getattr(msg, "tool_calls", None) or [])
    ]

    log_run(
        thread_id=thread_id,
        query=message,
        blocked=False,
        block_reason=None,
        tools_called=tools_called,
        latency_s=latency_s,
        response_preview=response,
    )

    return response


def ask_with_trace(agent, message: str, thread_id: str = "eval") -> dict:
    is_valid, reason = validate_input(message)

    if not is_valid:
        blocked_response = f"I can't process that message: {reason}"

        log_run(
            thread_id=thread_id,
            query=message,
            blocked=True,
            block_reason=reason,
            tools_called=[],
            latency_s=0.0,
            response_preview=blocked_response,
        )

        return {
            "response": blocked_response,
            "tools_called": [],
            "tool_calls": [],
            "blocked": True,
        }

    start = time.perf_counter()

    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
    )

    latency_s = time.perf_counter() - start

    tools_called = []
    tool_calls_detail = []

    for msg in result["messages"]:
        calls = getattr(msg, "tool_calls", None)

        if calls:
            for call in calls:
                tools_called.append(call["name"])
                tool_calls_detail.append({
                    "name": call["name"],
                    "args": call.get("args", {}),
                })

    response = result["messages"][-1].content

    log_run(
        thread_id=thread_id,
        query=message,
        blocked=False,
        block_reason=None,
        tools_called=tools_called,
        latency_s=latency_s,
        response_preview=response,
    )

    return {
        "response": response,
        "tools_called": tools_called,
        "tool_calls": tool_calls_detail,
        "blocked": False,
    }
