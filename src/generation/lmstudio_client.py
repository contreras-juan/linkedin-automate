from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv
import requests


DEFAULT_LMSTUDIO_BASE_URL = "http://192.168.0.15:1234/v1"
DEFAULT_LMSTUDIO_MODEL = "local-model"
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class LMStudioClientError(RuntimeError):
    """Raised when LMStudio cannot generate a valid chat completion."""


class LMStudioClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 60.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("LMSTUDIO_BASE_URL") or DEFAULT_LMSTUDIO_BASE_URL).rstrip("/")
        self.model = model or os.getenv("LMSTUDIO_MODEL") or DEFAULT_LMSTUDIO_MODEL
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LMStudioClientError("LMStudio chat completion request failed.") from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise LMStudioClientError("LMStudio returned invalid JSON.") from exc

        return self._extract_message_content(response_payload)

    @staticmethod
    def _extract_message_content(response_payload: dict[str, Any]) -> str:
        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LMStudioClientError("LMStudio response is missing message content.") from exc

        if not isinstance(content, str) or not content.strip():
            raise LMStudioClientError("LMStudio response message content is empty.")

        return content.strip()
