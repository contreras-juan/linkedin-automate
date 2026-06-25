from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.filtering.embedding_filter import ScoredPaper
from src.generation import LMStudioClient, LinkedInPostGenerator


@tool
def generate_linkedin_posts(
    scored_papers: list[dict[str, Any]],
    content_instructions: str | None = None,
) -> list[dict[str, Any]]:
    """Generate LinkedIn posts for scored arXiv papers using the configured LLM."""

    parsed_papers = [ScoredPaper.model_validate(scored_paper) for scored_paper in scored_papers]
    posts = LinkedInPostGenerator(client=LMStudioClient()).generate_posts(
        parsed_papers,
        content_instructions=content_instructions,
    )
    return [post.model_dump(mode="json") for post in posts]
