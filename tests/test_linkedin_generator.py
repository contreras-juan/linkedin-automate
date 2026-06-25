from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from src.filtering.embedding_filter import ScoredPaper
from src.generation.linkedin_generator import LinkedInPostGenerator
from src.ingestion.arxiv_client import ArxivPaper


class FakeChatClient:
    def __init__(self) -> None:
        self.messages: Sequence[dict[str, str]] | None = None
        self.temperature: float | None = None
        self.max_tokens: int | None = None

    def generate_chat_completion(
        self,
        messages: Sequence[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> str:
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        return (
            "La robotica esta entrando en una etapa donde los modelos aprenden priors de accion.\n\n"
            "Este paper muestra una forma de mejorar politicas Vision-Language-Action con "
            "preentrenamiento de movimiento antes de alinear vision y lenguaje.\n\n"
            "#IA #Robotica #Automatizacion #IA"
        )


def test_generate_post_builds_spanish_prompt_and_structured_output() -> None:
    client = FakeChatClient()
    generator = LinkedInPostGenerator(client=client, temperature=0.2, max_tokens=300)
    scored_paper = ScoredPaper(paper=_paper(), score=0.91)

    post = generator.generate_post(
        scored_paper,
        content_instructions="Use an executive tone for founders.",
    )

    assert post.source_title == "Learning Action Priors"
    assert str(post.source_url) == "https://arxiv.org/abs/2606.12345v1"
    assert post.score == 0.91
    assert post.hashtags == ["#IA", "#Robotica", "#Automatizacion"]
    assert "robotica esta entrando" in post.content
    assert client.temperature == 0.2
    assert client.max_tokens == 300
    assert client.messages is not None
    assert client.messages[0]["role"] == "system"
    assert "editor técnico" in client.messages[0]["content"]
    assert "120 a 180 palabras" in client.messages[1]["content"]
    assert "Learning Action Priors" in client.messages[1]["content"]
    assert "No inventes" not in client.messages[1]["content"]
    assert "no inventes" in client.messages[1]["content"]
    assert "Use an executive tone for founders." in client.messages[1]["content"]


def test_generate_posts_handles_multiple_scored_papers() -> None:
    generator = LinkedInPostGenerator(client=FakeChatClient())

    posts = generator.generate_posts([ScoredPaper(paper=_paper(), score=0.8)])

    assert len(posts) == 1
    assert posts[0].source_title == "Learning Action Priors"


def _paper() -> ArxivPaper:
    return ArxivPaper(
        title="Learning Action Priors",
        summary="A paper about action priors for robot manipulation and VLA models.",
        published_date=datetime(2026, 6, 24, tzinfo=timezone.utc),
        arxiv_url="https://arxiv.org/abs/2606.12345v1",
        authors=["Ada Lovelace", "Alan Turing"],
    )
