from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from src.filtering.embedding_filter import EmbeddingPaperFilter, FilterProfile
from src.ingestion.arxiv_client import ArxivPaper


class FakeEmbeddingProvider:
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        normalized_text = text.lower()
        if "agent" in normalized_text or "automation" in normalized_text:
            return [1.0, 0.0]
        if "statistics" in normalized_text:
            return [0.8, 0.6]
        if "biology" in normalized_text:
            return [0.0, 1.0]

        return [0.0, 0.0]


def test_filter_papers_orders_by_similarity_and_applies_limits() -> None:
    papers = [
        _paper("Biology discovery", "A paper about biology and wet labs."),
        _paper("Statistics methods", "A paper about statistics for experiments."),
        _paper("Agent automation", "A paper about agent workflows and automation."),
    ]
    profile = FilterProfile(
        name="ai automation",
        interests=["AI agents", "workflow automation"],
        min_score=0.7,
        max_results=2,
    )

    scored_papers = EmbeddingPaperFilter(FakeEmbeddingProvider()).filter_papers(papers, profile)

    assert [item.paper.title for item in scored_papers] == [
        "Agent automation",
        "Statistics methods",
    ]
    assert [round(item.score, 2) for item in scored_papers] == [1.0, 0.8]


def test_filter_papers_returns_empty_when_no_paper_reaches_threshold() -> None:
    papers = [_paper("Biology discovery", "A paper about biology and wet labs.")]
    profile = FilterProfile(
        name="ai automation",
        interests=["AI agents"],
        min_score=0.5,
        max_results=5,
    )

    scored_papers = EmbeddingPaperFilter(FakeEmbeddingProvider()).filter_papers(papers, profile)

    assert scored_papers == []


def test_filter_profile_loads_from_json_file(tmp_path: Path) -> None:
    profile_path = tmp_path / "filter_profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "name": "custom profile",
                "interests": ["LLM agents", "semantic search"],
                "min_score": 0.42,
                "max_results": 3,
            }
        ),
        encoding="utf-8",
    )

    profile = FilterProfile.from_json_file(profile_path)

    assert profile == FilterProfile(
        name="custom profile",
        interests=["LLM agents", "semantic search"],
        min_score=0.42,
        max_results=3,
    )


def _paper(title: str, summary: str) -> ArxivPaper:
    return ArxivPaper(
        title=title,
        summary=summary,
        published_date=datetime(2026, 6, 24, tzinfo=timezone.utc),
        arxiv_url="https://arxiv.org/abs/2606.12345v1",
        authors=["Ada Lovelace"],
    )
