from unittest.mock import Mock

import pytest

from src.generation.llm_client import (
    AnthropicClient,
    GoogleClient,
    LLMClientConfig,
    LLMClientError,
    OllamaClient,
    OpenAICompatibleClient,
    create_llm_client,
    llm_config_from_env,
)


def test_llm_config_from_env_supports_lmstudio_fallbacks(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("LMSTUDIO_MODEL", "local-model")
    monkeypatch.setenv("LMSTUDIO_BASE_URL", "http://local/v1")

    config = llm_config_from_env()

    assert config.provider == "lmstudio"
    assert config.model == "local-model"
    assert config.base_url == "http://local/v1"


def test_create_llm_client_returns_openai_compatible_for_openai(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    client = create_llm_client()

    assert isinstance(client, OpenAICompatibleClient)


def test_openai_compatible_client_sends_chat_completion_payload() -> None:
    session = _session_with_payload({"choices": [{"message": {"content": "Generated post"}}]})
    client = OpenAICompatibleClient(
        config=LLMClientConfig(
            provider="openai",
            model="gpt-test",
            base_url="https://api.openai.com/v1",
            api_key="secret",
            timeout_seconds=12,
        ),
        session=session,
    )

    content = client.generate_chat_completion(
        messages=[{"role": "user", "content": "Write a post"}],
        temperature=0.3,
        max_tokens=200,
    )

    assert content == "Generated post"
    session.post.assert_called_once_with(
        "https://api.openai.com/v1/chat/completions",
        json={
            "model": "gpt-test",
            "messages": [{"role": "user", "content": "Write a post"}],
            "temperature": 0.3,
            "max_tokens": 200,
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
        },
        timeout=12,
    )


def test_anthropic_client_maps_system_prompt_and_extracts_text() -> None:
    session = _session_with_payload({"content": [{"type": "text", "text": "Claude draft"}]})
    client = AnthropicClient(
        config=LLMClientConfig(
            provider="anthropic",
            model="claude-test",
            base_url="https://api.anthropic.com/v1",
            api_key="secret",
        ),
        session=session,
    )

    content = client.generate_chat_completion(
        messages=[
            {"role": "system", "content": "Be accurate."},
            {"role": "user", "content": "Write a post"},
        ]
    )

    assert content == "Claude draft"
    payload = session.post.call_args.kwargs["json"]
    assert payload["system"] == "Be accurate."
    assert payload["messages"] == [{"role": "user", "content": "Write a post"}]


def test_google_client_maps_messages_and_extracts_text() -> None:
    session = _session_with_payload(
        {"candidates": [{"content": {"parts": [{"text": "Gemini draft"}]}}]}
    )
    client = GoogleClient(
        config=LLMClientConfig(
            provider="google",
            model="gemini-test",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key="secret",
        ),
        session=session,
    )

    content = client.generate_chat_completion(
        messages=[{"role": "user", "content": "Write a post"}],
        temperature=0.2,
        max_tokens=100,
    )

    assert content == "Gemini draft"
    assert session.post.call_args.args[0].endswith("/models/gemini-test:generateContent?key=secret")
    assert session.post.call_args.kwargs["json"]["generationConfig"] == {
        "temperature": 0.2,
        "maxOutputTokens": 100,
    }


def test_ollama_client_sends_chat_payload_and_extracts_text() -> None:
    session = _session_with_payload({"message": {"content": "Ollama draft"}})
    client = OllamaClient(
        config=LLMClientConfig(
            provider="ollama",
            model="llama3.1",
            base_url="http://localhost:11434",
        ),
        session=session,
    )

    content = client.generate_chat_completion(
        messages=[{"role": "user", "content": "Write a post"}],
        temperature=0.4,
        max_tokens=150,
    )

    assert content == "Ollama draft"
    assert session.post.call_args.args[0] == "http://localhost:11434/api/chat"
    assert session.post.call_args.kwargs["json"]["options"] == {
        "temperature": 0.4,
        "num_predict": 150,
    }


def test_provider_requiring_key_fails_without_key() -> None:
    with pytest.raises(LLMClientError, match="ANTHROPIC_API_KEY"):
        AnthropicClient(
            config=LLMClientConfig(
                provider="anthropic",
                model="claude-test",
                base_url="https://api.anthropic.com/v1",
            )
        )


def _session_with_payload(payload: dict) -> Mock:
    session = Mock()
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    session.post.return_value = response
    return session
