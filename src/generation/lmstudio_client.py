from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv
import requests

from src.generation.llm_client import (
    DEFAULT_LMSTUDIO_BASE_URL,
    DEFAULT_LMSTUDIO_MODEL,
    LLMClientConfig,
    LLMClientError,
    OpenAICompatibleClient,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class LMStudioClientError(LLMClientError):
    """Raised when LMStudio cannot generate a valid chat completion."""


class LMStudioClient(OpenAICompatibleClient):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 60.0,
        session: requests.Session | None = None,
    ) -> None:
        config = LLMClientConfig(
            provider="lmstudio",
            base_url=base_url or os.getenv("LMSTUDIO_BASE_URL") or DEFAULT_LMSTUDIO_BASE_URL,
            model=model or os.getenv("LMSTUDIO_MODEL") or DEFAULT_LMSTUDIO_MODEL,
            timeout_seconds=timeout_seconds,
        )
        super().__init__(config=config, session=session)

    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        try:
            return super().generate_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMClientError as exc:
            raise LMStudioClientError(str(exc)) from exc
