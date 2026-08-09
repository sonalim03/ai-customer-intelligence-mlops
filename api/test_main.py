"""
Tests for the FastAPI layer. FinSight uses a local Ollama model, so there's
no API key to mock around — instead these tests verify the API behaves
correctly when the agent can't be built (e.g. langgraph/langchain-ollama
construction fails) or when a chat request fails at call time (e.g. Ollama
isn't running). Neither case needs a live Ollama server.

Run: pytest api/test_main.py -v
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200


def test_health_check_does_not_crash_when_agent_unavailable():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    # agent_ready reflects whether build_agent() succeeded in THIS
    # environment (e.g. whether Ollama is reachable) — either value is
    # fine here, the point is /health must never itself error out.


def test_chat_returns_clean_503_when_agent_build_failed(monkeypatch):
    # Simulate build_agent() having failed (e.g. Ollama unreachable at
    # startup) without needing a real Ollama server.
    import api.main as main_module
    monkeypatch.setitem(main_module._agent_cache, "agent", None)
    monkeypatch.setitem(
        main_module._agent_cache, "error",
        "Could not connect to Ollama at http://localhost:11434",
    )

    r = client.post("/chat", json={"message": "What is AAPL trading at?"})
    assert r.status_code == 503
    assert "Ollama" in r.json()["detail"]


def test_chat_returns_clean_500_when_ask_with_trace_raises(monkeypatch):
    # Simulate a live agent that fails DURING a call (e.g. Ollama was up
    # when the app started but drops mid-request) — this exercises the
    # try/except around ask_with_trace() in api/main.py's chat() handler.
    import api.main as main_module
    monkeypatch.setitem(main_module._agent_cache, "agent", object())  # any non-None value

    def _raise(*args, **kwargs):
        raise ConnectionError("Ollama connection lost")

    monkeypatch.setattr(main_module, "ask_with_trace", _raise)

    r = client.post("/chat", json={"message": "What is AAPL trading at?"})
    assert r.status_code == 500
    assert "Ollama connection lost" in r.json()["detail"]


def test_chat_rejects_empty_message_with_422():
    r = client.post("/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_rejects_oversized_message_with_422():
    r = client.post("/chat", json={"message": "a" * 5000})
    assert r.status_code == 422


def test_logs_summary_endpoint_works_with_no_logs():
    r = client.get("/logs/summary")
    assert r.status_code == 200
    assert "total_runs" in r.json()
