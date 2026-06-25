from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.filtering.embedding_filter import ScoredPaper
from src.generation.linkedin_generator import LinkedInPost
from src.ingestion.arxiv_client import ArxivPaper
from src.tools.curator_tool import score_papers_by_embedding
from src.tools.reviewer_tool import review_linkedin_posts
from src.tools.writer_tool import generate_linkedin_posts


def test_score_papers_by_embedding_wraps_filtering_service() -> None:
    paper = _paper()
    scored_paper = ScoredPaper(paper=paper, score=0.8)
    filter_instance = Mock()
    filter_instance.filter_papers.return_value = [scored_paper]

    with (
        patch("src.tools.curator_tool.FilterProfile.from_json_file") as profile_loader,
        patch("src.tools.curator_tool.SentenceTransformerEmbeddingProvider"),
        patch("src.tools.curator_tool.EmbeddingPaperFilter", return_value=filter_instance),
    ):
        result = score_papers_by_embedding.invoke(
            {"papers": [paper.model_dump(mode="json")], "profile_path": "profile.json"}
        )

    profile_loader.assert_called_once_with("profile.json")
    assert result == [scored_paper.model_dump(mode="json")]


def test_score_papers_by_embedding_accepts_inline_profile() -> None:
    paper = _paper()
    scored_paper = ScoredPaper(paper=paper, score=0.8)
    filter_instance = Mock()
    filter_instance.filter_papers.return_value = [scored_paper]

    with (
        patch("src.tools.curator_tool.FilterProfile.from_json_file") as profile_loader,
        patch("src.tools.curator_tool.SentenceTransformerEmbeddingProvider"),
        patch("src.tools.curator_tool.EmbeddingPaperFilter", return_value=filter_instance),
    ):
        result = score_papers_by_embedding.invoke(
            {
                "papers": [paper.model_dump(mode="json")],
                "profile": {
                    "name": "dynamic",
                    "interests": ["computer vision"],
                    "min_score": 0.1,
                    "max_results": 2,
                },
            }
        )

    profile_loader.assert_not_called()
    assert result == [scored_paper.model_dump(mode="json")]


def test_generate_linkedin_posts_wraps_generation_service() -> None:
    paper = _paper()
    scored_paper = ScoredPaper(paper=paper, score=0.8)
    post = LinkedInPost(
        source_title=paper.title,
        source_url=paper.arxiv_url,
        score=0.8,
        content="Agentic Research is relevant. #AI",
        hashtags=["#AI"],
    )
    generator_instance = Mock()
    generator_instance.generate_posts.return_value = [post]

    with (
        patch("src.tools.writer_tool.LMStudioClient"),
        patch("src.tools.writer_tool.LinkedInPostGenerator", return_value=generator_instance),
    ):
        result = generate_linkedin_posts.invoke(
            {
                "scored_papers": [scored_paper.model_dump(mode="json")],
                "content_instructions": "Use an executive tone.",
            }
        )

    generator_instance.generate_posts.assert_called_once()
    assert generator_instance.generate_posts.call_args.kwargs == {
        "content_instructions": "Use an executive tone."
    }
    assert result == [post.model_dump(mode="json")]


def test_review_linkedin_posts_flags_risky_claims() -> None:
    result = review_linkedin_posts.invoke(
        {
            "posts": [
                {
                    "source_title": "Agentic Research",
                    "source_url": "https://arxiv.org/abs/2606.00001v1",
                    "score": 0.8,
                    "content": "Agentic Research garantiza resultados sin errores. #AI",
                    "hashtags": ["#AI"],
                }
            ]
        }
    )

    assert result == [
        {
            "source_title": "Agentic Research",
            "approved": False,
            "notes": ["Post contains risky absolute claims: garantiza, sin errores."],
        }
    ]


def _paper() -> ArxivPaper:
    return ArxivPaper(
        title="Agentic Research",
        summary="A paper about multi-agent research automation.",
        published_date=datetime(2026, 6, 25, tzinfo=timezone.utc),
        arxiv_url="https://arxiv.org/abs/2606.00001v1",
        authors=["Ada Lovelace"],
    )
