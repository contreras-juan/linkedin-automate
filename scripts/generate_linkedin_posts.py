from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.filtering.embedding_filter import ScoredPaper  # noqa: E402
from src.generation import LinkedInPostGenerator, create_llm_client  # noqa: E402


INPUT_PATH = PROJECT_ROOT / "data" / "filtered_arxiv_sample.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "generated_linkedin_posts.json"


def main() -> None:
    raw_scored_papers = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    scored_papers = [ScoredPaper.model_validate(raw_paper) for raw_paper in raw_scored_papers]

    generator = LinkedInPostGenerator(client=create_llm_client())
    posts = generator.generate_posts(scored_papers)

    OUTPUT_PATH.write_text(
        json.dumps([post.model_dump(mode="json") for post in posts], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(posts)} posts to {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
