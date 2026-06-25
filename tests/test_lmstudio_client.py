from unittest.mock import Mock

import pytest
import requests

from src.generation.lmstudio_client import LMStudioClient, LMStudioClientError


def test_generate_chat_completion_sends_openai_compatible_payload() -> None:
    session = Mock()
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": "Generated post"}}]}
    response.raise_for_status.return_value = None
    session.post.return_value = response
    client = LMStudioClient(
        base_url="http://localhost:1234/v1/",
        model="test-model",
        timeout_seconds=12,
        session=session,
    )

    content = client.generate_chat_completion(
        messages=[{"role": "user", "content": "Write a post"}],
        temperature=0.3,
        max_tokens=200,
    )

    assert content == "Generated post"
    session.post.assert_called_once_with(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Write a post"}],
            "temperature": 0.3,
            "max_tokens": 200,
        },
        timeout=12,
    )


def test_generate_chat_completion_wraps_request_errors() -> None:
    session = Mock()
    session.post.side_effect = requests.ConnectionError("connection refused")
    client = LMStudioClient(session=session)

    with pytest.raises(LMStudioClientError, match="request failed"):
        client.generate_chat_completion(messages=[{"role": "user", "content": "Hello"}])


def test_generate_chat_completion_rejects_missing_content() -> None:
    session = Mock()
    response = Mock()
    response.json.return_value = {"choices": [{"message": {}}]}
    response.raise_for_status.return_value = None
    session.post.return_value = response
    client = LMStudioClient(session=session)

    with pytest.raises(LMStudioClientError, match="missing message content"):
        client.generate_chat_completion(messages=[{"role": "user", "content": "Hello"}])
