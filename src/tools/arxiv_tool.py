from __future__ import annotations

from typing import Sequence

from langchain_core.tools import tool

from src.ingestion.arxiv_client import ArxivClient


DEFAULT_RESEARCH_CATEGORIES = ("cs.CL", "cs.AI", "cs.LG")


@tool
def search_recent_arxiv_papers(
    categories: Sequence[str] = DEFAULT_RESEARCH_CATEGORIES,
    max_results: int = 10,
) -> list[dict[str, object]]:
    """Search recent arXiv papers for the given categories."""

    papers = ArxivClient(categories=categories, max_results=max_results).fetch_recent_papers()
    return [paper.model_dump(mode="json") for paper in papers]
