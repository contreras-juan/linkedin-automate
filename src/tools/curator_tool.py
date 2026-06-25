from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.filtering.embedding_filter import (
    EmbeddingPaperFilter,
    FilterProfile,
    SentenceTransformerEmbeddingProvider,
)
from src.ingestion.arxiv_client import ArxivPaper


DEFAULT_FILTER_PROFILE_PATH = "config/filter_profile.json"


@tool
def score_papers_by_embedding(
    papers: list[dict[str, Any]],
    profile_path: str = DEFAULT_FILTER_PROFILE_PATH,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Score arXiv papers against the configured semantic interest profile."""

    arxiv_papers = [ArxivPaper.model_validate(paper) for paper in papers]
    filter_profile = (
        FilterProfile.model_validate(profile)
        if profile is not None
        else FilterProfile.from_json_file(profile_path)
    )
    scored_papers = EmbeddingPaperFilter(
        SentenceTransformerEmbeddingProvider()
    ).filter_papers(arxiv_papers, filter_profile)

    return [scored_paper.model_dump(mode="json") for scored_paper in scored_papers]
