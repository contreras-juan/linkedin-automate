from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, Sequence

from dotenv import load_dotenv
import requests


LLMProvider = Literal["lmstudio", "openai", "google", "anthropic", "ollama"]

DEFAULT_LMSTUDIO_BASE_URL = "http://192.168.0.15:1234/v1"
DEFAULT_LMSTUDIO_MODEL = "local-model"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GOOGLE_MODEL = "gemini-1.5-flash"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-haiku-latest"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1"

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class LLMClientError(RuntimeError):
    """Raised when the configured LLM provider cannot generate content."""


class LLMClient(Protocol):
    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        """Generate content from a chat-style prompt."""


@dataclass(frozen=True)
class LLMClientConfig:
    provider: LLMProvider
    model: str
    base_url: str
    api_key: str | None = None
    timeout_seconds: float = 60.0


class OpenAICompatibleClient:
    def __init__(
        self,
        config: LLMClientConfig,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()

    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        headers = _json_headers(self.config.api_key)
        payload = {
            "model": self.config.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response_payload = _post_json(
            session=self.session,
            url=f"{self.config.base_url.rstrip('/')}/chat/completions",
            payload=payload,
            headers=headers,
            timeout_seconds=self.config.timeout_seconds,
            provider=self.config.provider,
        )
        return _extract_openai_message_content(response_payload, self.config.provider)


class AnthropicClient:
    def __init__(
        self,
        config: LLMClientConfig,
        session: requests.Session | None = None,
    ) -> None:
        if not config.api_key:
            raise LLMClientError("ANTHROPIC_API_KEY is required for provider 'anthropic'.")

        self.config = config
        self.session = session or requests.Session()

    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        system_prompt, anthropic_messages = _split_system_messages(messages)
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response_payload = _post_json(
            session=self.session,
            url=f"{self.config.base_url.rstrip('/')}/messages",
            payload=payload,
            headers={
                "anthropic-version": "2023-06-01",
                **_json_headers(self.config.api_key),
            },
            timeout_seconds=self.config.timeout_seconds,
            provider=self.config.provider,
        )
        return _extract_anthropic_content(response_payload)


class GoogleClient:
    def __init__(
        self,
        config: LLMClientConfig,
        session: requests.Session | None = None,
    ) -> None:
        if not config.api_key:
            raise LLMClientError("GOOGLE_API_KEY is required for provider 'google'.")

        self.config = config
        self.session = session or requests.Session()

    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        payload = {
            "contents": _to_google_contents(messages),
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        response_payload = _post_json(
            session=self.session,
            url=(
                f"{self.config.base_url.rstrip('/')}/models/"
                f"{self.config.model}:generateContent?key={self.config.api_key}"
            ),
            payload=payload,
            headers={"Content-Type": "application/json"},
            timeout_seconds=self.config.timeout_seconds,
            provider=self.config.provider,
        )
        return _extract_google_content(response_payload)


class OllamaClient:
    def __init__(
        self,
        config: LLMClientConfig,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()

    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        payload = {
            "model": self.config.model,
            "messages": list(messages),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        response_payload = _post_json(
            session=self.session,
            url=f"{self.config.base_url.rstrip('/')}/api/chat",
            payload=payload,
            headers={"Content-Type": "application/json"},
            timeout_seconds=self.config.timeout_seconds,
            provider=self.config.provider,
        )
        return _extract_ollama_content(response_payload)


def create_llm_client(
    config: LLMClientConfig | None = None,
    session: requests.Session | None = None,
) -> LLMClient:
    resolved_config = config or llm_config_from_env()

    if resolved_config.provider in {"lmstudio", "openai"}:
        return OpenAICompatibleClient(config=resolved_config, session=session)
    if resolved_config.provider == "anthropic":
        return AnthropicClient(config=resolved_config, session=session)
    if resolved_config.provider == "google":
        return GoogleClient(config=resolved_config, session=session)
    if resolved_config.provider == "ollama":
        return OllamaClient(config=resolved_config, session=session)

    raise LLMClientError(f"Unsupported LLM provider: {resolved_config.provider}")


def llm_config_from_env() -> LLMClientConfig:
    provider = _provider_from_env()
    timeout_seconds = _float_env("LLM_TIMEOUT_SECONDS", 60.0)
    model = os.getenv("LLM_MODEL") or _default_model(provider)
    base_url = os.getenv("LLM_BASE_URL") or _default_base_url(provider)
    api_key = _api_key_for_provider(provider)

    if provider == "lmstudio":
        model = os.getenv("LLM_MODEL") or os.getenv("LMSTUDIO_MODEL") or DEFAULT_LMSTUDIO_MODEL
        base_url = (
            os.getenv("LLM_BASE_URL")
            or os.getenv("LMSTUDIO_BASE_URL")
            or DEFAULT_LMSTUDIO_BASE_URL
        )

    return LLMClientConfig(
        provider=provider,
        model=model,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )


def _provider_from_env() -> LLMProvider:
    raw_provider = os.getenv("LLM_PROVIDER", "lmstudio").strip().lower()
    if raw_provider in {"lmstudio", "openai", "google", "anthropic", "ollama"}:
        return raw_provider

    raise LLMClientError(
        "LLM_PROVIDER must be one of: lmstudio, openai, google, anthropic, ollama."
    )


def _default_model(provider: LLMProvider) -> str:
    return {
        "lmstudio": DEFAULT_LMSTUDIO_MODEL,
        "openai": DEFAULT_OPENAI_MODEL,
        "google": DEFAULT_GOOGLE_MODEL,
        "anthropic": DEFAULT_ANTHROPIC_MODEL,
        "ollama": DEFAULT_OLLAMA_MODEL,
    }[provider]


def _default_base_url(provider: LLMProvider) -> str:
    return {
        "lmstudio": DEFAULT_LMSTUDIO_BASE_URL,
        "openai": DEFAULT_OPENAI_BASE_URL,
        "google": DEFAULT_GOOGLE_BASE_URL,
        "anthropic": DEFAULT_ANTHROPIC_BASE_URL,
        "ollama": DEFAULT_OLLAMA_BASE_URL,
    }[provider]


def _api_key_for_provider(provider: LLMProvider) -> str | None:
    generic_key = os.getenv("LLM_API_KEY")
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY") or generic_key
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY") or generic_key
    if provider == "google":
        return os.getenv("GOOGLE_API_KEY") or generic_key

    return generic_key


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError:
        return default


def _json_headers(api_key: str | None = None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return headers


def _post_json(
    session: requests.Session,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
    provider: str,
) -> dict[str, Any]:
    try:
        response = session.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LLMClientError(f"{provider} chat completion request failed.") from exc

    try:
        response_payload = response.json()
    except ValueError as exc:
        raise LLMClientError(f"{provider} returned invalid JSON.") from exc

    if not isinstance(response_payload, dict):
        raise LLMClientError(f"{provider} returned an invalid response payload.")

    return response_payload


def _extract_openai_message_content(response_payload: dict[str, Any], provider: str) -> str:
    try:
        content = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMClientError(f"{provider} response is missing message content.") from exc

    return _validate_content(content, provider)


def _extract_anthropic_content(response_payload: dict[str, Any]) -> str:
    try:
        blocks = response_payload["content"]
    except KeyError as exc:
        raise LLMClientError("anthropic response is missing content.") from exc

    if not isinstance(blocks, list):
        raise LLMClientError("anthropic response content has invalid shape.")

    text_parts = [
        block.get("text", "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return _validate_content("\n".join(text_parts), "anthropic")


def _extract_google_content(response_payload: dict[str, Any]) -> str:
    try:
        parts = response_payload["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMClientError("google response is missing content.") from exc

    if not isinstance(parts, list):
        raise LLMClientError("google response content has invalid shape.")

    text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return _validate_content("\n".join(text_parts), "google")


def _extract_ollama_content(response_payload: dict[str, Any]) -> str:
    try:
        content = response_payload["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise LLMClientError("ollama response is missing message content.") from exc

    return _validate_content(content, "ollama")


def _validate_content(content: Any, provider: str) -> str:
    if not isinstance(content, str) or not content.strip():
        raise LLMClientError(f"{provider} response message content is empty.")

    return content.strip()


def _split_system_messages(
    messages: Sequence[dict[str, str]],
) -> tuple[str | None, list[dict[str, str]]]:
    system_messages: list[str] = []
    provider_messages: list[dict[str, str]] = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_messages.append(content)
            continue

        provider_messages.append(
            {
                "role": "assistant" if role == "assistant" else "user",
                "content": content,
            }
        )

    return ("\n\n".join(system_messages) or None, provider_messages)


def _to_google_contents(messages: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    system_prompt, provider_messages = _split_system_messages(messages)

    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})

    for message in provider_messages:
        role = "model" if message["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": message["content"]}]})

    return contents
