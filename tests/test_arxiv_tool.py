from datetime import datetime, timezone
from unittest.mock import Mock, patch

from langchain_core.tools import BaseTool

from src.ingestion.arxiv_client import ArxivPaper
from src.tools.arxiv_tool import search_recent_arxiv_papers


def test_search_recent_arxiv_papers_is_langchain_tool() -> None:
    assert isinstance(search_recent_arxiv_papers, BaseTool)


def test_search_recent_arxiv_papers_returns_json_serializable_papers() -> None:
    paper = ArxivPaper(
        title="Agentic Research",
        summary="A paper about multi-agent research automation.",
        published_date=datetime(2026, 6, 25, tzinfo=timezone.utc),
        arxiv_url="https://arxiv.org/abs/2606.00001v1",
        authors=["Ada Lovelace"],
    )
    client_instance = Mock()
    client_instance.fetch_recent_papers.return_value = [paper]

    with patch("src.tools.arxiv_tool.ArxivClient", return_value=client_instance) as client_class:
        result = search_recent_arxiv_papers.invoke(
            {"categories": ["cs.AI"], "max_results": 1}
        )

    client_class.assert_called_once_with(categories=["cs.AI"], max_results=1)
    assert result == [
        {
            "title": "Agentic Research",
            "summary": "A paper about multi-agent research automation.",
            "published_date": "2026-06-25T00:00:00Z",
            "arxiv_url": "https://arxiv.org/abs/2606.00001v1",
            "authors": ["Ada Lovelace"],
        }
    ]
