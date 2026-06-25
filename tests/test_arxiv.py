from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import requests

from src.ingestion.arxiv_client import ArxivClient, ArxivClientError, ArxivPaper


SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://arxiv.org/abs/2606.12345v1</id>
    <published>2026-06-24T15:30:00Z</published>
    <title>
      A Robust Test Paper
    </title>
    <summary>
      This paper validates that whitespace is normalized
      when parsing arXiv Atom feeds.
    </summary>
    <author>
      <name>Ada Lovelace</name>
    </author>
    <author>
      <name>Alan Turing</name>
    </author>
  </entry>
</feed>
"""


def test_fetch_recent_papers_formats_arxiv_feed() -> None:
    session = Mock()
    response = Mock()
    response.text = SAMPLE_FEED
    response.raise_for_status.return_value = None
    session.get.return_value = response

    client = ArxivClient(categories=("cs.CL", "cs.AI"), max_results=5, session=session)

    papers = client.fetch_recent_papers()

    assert papers == [
        ArxivPaper(
            title="A Robust Test Paper",
            summary=(
                "This paper validates that whitespace is normalized "
                "when parsing arXiv Atom feeds."
            ),
            published_date=datetime(2026, 6, 24, 15, 30, tzinfo=timezone.utc),
            arxiv_url="https://arxiv.org/abs/2606.12345v1",
            authors=["Ada Lovelace", "Alan Turing"],
        )
    ]
    session.get.assert_called_once_with(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": "cat:cs.CL OR cat:cs.AI",
            "start": 0,
            "max_results": 5,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
        timeout=10.0,
    )


def test_fetch_recent_papers_wraps_http_errors() -> None:
    session = Mock()
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("503")
    session.get.return_value = response

    client = ArxivClient(session=session)

    with pytest.raises(ArxivClientError, match="request failed"):
        client.fetch_recent_papers()


def test_fetch_recent_papers_rejects_invalid_xml() -> None:
    session = Mock()
    response = Mock()
    response.text = "<not valid"
    response.raise_for_status.return_value = None
    session.get.return_value = response

    client = ArxivClient(session=session)

    with pytest.raises(ArxivClientError, match="invalid XML"):
        client.fetch_recent_papers()


def test_client_requires_at_least_one_category() -> None:
    with pytest.raises(ValueError, match="At least one"):
        ArxivClient(categories=(" ", ""))
