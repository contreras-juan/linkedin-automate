from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field

from src.ingestion.arxiv_client import ArxivPaper


DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


class FilterProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    interests: list[str] = Field(min_length=1)
    min_score: float = Field(default=0.25, ge=-1.0, le=1.0)
    max_results: int = Field(default=5, ge=1)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "FilterProfile":
        raw_profile = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw_profile)


class ScoredPaper(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper: ArxivPaper
    score: float


class SentenceTransformerEmbeddingProvider:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        return [embedding.tolist() for embedding in embeddings]


class EmbeddingPaperFilter:
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider

    def filter_papers(
        self,
        papers: Sequence[ArxivPaper],
        profile: FilterProfile,
    ) -> list[ScoredPaper]:
        if not papers:
            return []

        profile_vector = self._average_vectors(self.embedding_provider.embed_texts(profile.interests))
        paper_texts = [self._paper_text(paper) for paper in papers]
        paper_vectors = self.embedding_provider.embed_texts(paper_texts)

        scored_papers = [
            ScoredPaper(paper=paper, score=self._cosine_similarity(profile_vector, paper_vector))
            for paper, paper_vector in zip(papers, paper_vectors, strict=True)
        ]

        relevant_papers = [paper for paper in scored_papers if paper.score >= profile.min_score]
        return sorted(relevant_papers, key=lambda paper: paper.score, reverse=True)[: profile.max_results]

    @staticmethod
    def _paper_text(paper: ArxivPaper) -> str:
        return f"{paper.title}\n\n{paper.summary}"

    @staticmethod
    def _average_vectors(vectors: Sequence[Sequence[float]]) -> list[float]:
        if not vectors:
            raise ValueError("At least one vector is required.")

        vector_size = len(vectors[0])
        if vector_size == 0:
            raise ValueError("Embedding vectors cannot be empty.")

        totals = [0.0] * vector_size
        for vector in vectors:
            if len(vector) != vector_size:
                raise ValueError("Embedding vectors must have the same dimensions.")
            for index, value in enumerate(vector):
                totals[index] += value

        return [value / len(vectors) for value in totals]

    @staticmethod
    def _cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
        if len(first) != len(second):
            raise ValueError("Embedding vectors must have the same dimensions.")

        first_norm = math.sqrt(sum(value * value for value in first))
        second_norm = math.sqrt(sum(value * value for value in second))
        if first_norm == 0.0 or second_norm == 0.0:
            return 0.0

        dot_product = sum(left * right for left, right in zip(first, second, strict=True))
        return dot_product / (first_norm * second_norm)
