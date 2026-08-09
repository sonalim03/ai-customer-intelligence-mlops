"""
Tests for agent/graph.py's provider dispatch (_build_llm). These verify
the RIGHT client class gets constructed with the RIGHT arguments for
each LLM_PROVIDER value — without needing a live Ollama server or real
AWS credentials. The actual client classes are monkeypatched.

Run: pytest agent/test_provider.py -v
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from agent.graph import _build_llm


def test_ollama_provider_uses_defaults(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    captured = {}

    class FakeChatOllama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_ollama.ChatOllama", FakeChatOllama)

    llm = _build_llm("ollama")

    assert isinstance(llm, FakeChatOllama)
    assert captured["model"] == "llama3.2:3b"
    assert captured["base_url"] == "http://localhost:11434"
    assert captured["temperature"] == 0


def test_ollama_provider_respects_env_overrides(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:1b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama-host:11434")

    captured = {}

    class FakeChatOllama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_ollama.ChatOllama", FakeChatOllama)

    _build_llm("ollama")

    assert captured["model"] == "llama3.2:1b"
    assert captured["base_url"] == "http://ollama-host:11434"


def test_bedrock_provider_uses_defaults(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)

    captured = {}

    class FakeChatBedrockConverse:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_aws.ChatBedrockConverse", FakeChatBedrockConverse)

    llm = _build_llm("bedrock")

    assert isinstance(llm, FakeChatBedrockConverse)
    assert captured["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    assert captured["region_name"] == "us-east-1"
    # Confirms no API key / secret is ever passed — auth is via the
    # IAM task role's default credential chain, not a code-level secret.
    assert "api_key" not in captured
    assert "aws_access_key_id" not in captured


def test_bedrock_provider_respects_env_overrides(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")

    captured = {}

    class FakeChatBedrockConverse:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("langchain_aws.ChatBedrockConverse", FakeChatBedrockConverse)

    _build_llm("bedrock")

    assert captured["model"] == "anthropic.claude-3-haiku-20240307-v1:0"
    assert captured["region_name"] == "eu-west-1"


def test_unknown_provider_raises_clear_error():
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        _build_llm("some-typo")
