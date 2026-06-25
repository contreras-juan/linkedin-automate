from __future__ import annotations

import re
from typing import Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.filtering.embedding_filter import ScoredPaper


HASHTAG_PATTERN = re.compile(r"#[\wáéíóúÁÉÍÓÚñÑ]+")


class ChatCompletionClient(Protocol):
    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        """Generate a chat completion from a chat-style prompt."""


class LinkedInPost(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_title: str = Field(min_length=1)
    source_url: HttpUrl
    score: float
    content: str = Field(min_length=1)
    hashtags: list[str] = Field(default_factory=list)


class LinkedInPostGenerator:
    def __init__(
        self,
        client: ChatCompletionClient,
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> None:
        self.client = client
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate_posts(
        self,
        scored_papers: Sequence[ScoredPaper],
        content_instructions: str | None = None,
    ) -> list[LinkedInPost]:
        return [
            self.generate_post(scored_paper, content_instructions=content_instructions)
            for scored_paper in scored_papers
        ]

    def generate_post(
        self,
        scored_paper: ScoredPaper,
        content_instructions: str | None = None,
    ) -> LinkedInPost:
        paper = scored_paper.paper
        content = self.client.generate_chat_completion(
            messages=self._build_messages(scored_paper, content_instructions),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return LinkedInPost(
            source_title=paper.title,
            source_url=paper.arxiv_url,
            score=scored_paper.score,
            content=content,
            hashtags=self._extract_hashtags(content),
        )

    def _build_messages(
        self,
        scored_paper: ScoredPaper,
        content_instructions: str | None = None,
    ) -> list[dict[str, str]]:
        paper = scored_paper.paper
        authors = ", ".join(paper.authors) if paper.authors else "Autores no especificados"
        extra_instructions = (
            f"\nInstrucciones adicionales del usuario: {content_instructions.strip()}\n"
            if content_instructions and content_instructions.strip()
            else ""
        )
        user_prompt = f"""
Genera una publicación de LinkedIn en español profesional y divulgativo.

Requisitos:
- 120 a 180 palabras.
- Empieza con un hook claro.
- Explica por qué el paper importa para IA aplicada, automatización o producto.
- Evita exageraciones y no inventes resultados que no estén en el resumen.
- Termina con 3 a 5 hashtags relevantes.
{extra_instructions}

Paper:
Título: {paper.title}
Autores: {authors}
Publicado: {paper.published_date.date().isoformat()}
URL: {paper.arxiv_url}
Score de relevancia: {scored_paper.score:.3f}
Resumen: {paper.summary}
""".strip()

        return [
            {
                "role": "system",
                "content": (
                    "Eres un editor técnico que transforma papers de IA en posts de LinkedIn "
                    "claros, útiles y fieles al contenido original."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _extract_hashtags(content: str) -> list[str]:
        hashtags: list[str] = []
        seen: set[str] = set()
        for hashtag in HASHTAG_PATTERN.findall(content):
            normalized = hashtag.lower()
            if normalized not in seen:
                hashtags.append(hashtag)
                seen.add(normalized)

        return hashtags
