from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.filtering.embedding_filter import (  # noqa: E402
    EmbeddingPaperFilter,
    FilterProfile,
    SentenceTransformerEmbeddingProvider,
)
from src.ingestion.arxiv_client import ArxivPaper  # noqa: E402


INPUT_PATH = PROJECT_ROOT / "data" / "arxiv_sample.json"
PROFILE_PATH = PROJECT_ROOT / "config" / "filter_profile.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "filtered_arxiv_sample.json"


def main() -> None:
    raw_papers = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    papers = [ArxivPaper.model_validate(raw_paper) for raw_paper in raw_papers]
    profile = FilterProfile.from_json_file(PROFILE_PATH)

    filter_service = EmbeddingPaperFilter(SentenceTransformerEmbeddingProvider())
    scored_papers = filter_service.filter_papers(papers, profile)

    OUTPUT_PATH.write_text(
        json.dumps([paper.model_dump(mode="json") for paper in scored_papers], indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(scored_papers)} papers to {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
