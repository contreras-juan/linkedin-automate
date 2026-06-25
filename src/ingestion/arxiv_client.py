from __future__ import annotations

from datetime import datetime
from typing import Iterable
from xml.etree import ElementTree

import requests
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
DEFAULT_CATEGORIES = ("cs.CL", "cs.AI", "cs.LG")


class ArxivClientError(RuntimeError):
    """Raised when the arXiv API request or response parsing fails."""


class ArxivPaper(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    published_date: datetime
    arxiv_url: HttpUrl
    authors: list[str] = Field(default_factory=list)


class ArxivClient:
    base_url = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        categories: Iterable[str] = DEFAULT_CATEGORIES,
        max_results: int = 10,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        category_list = [category.strip() for category in categories if category.strip()]
        if not category_list:
            raise ValueError("At least one arXiv category is required.")
        if max_results < 1:
            raise ValueError("max_results must be greater than zero.")

        self.categories = tuple(category_list)
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def fetch_recent_papers(self) -> list[ArxivPaper]:
        response = self.session.get(
            self.base_url,
            params=self._build_query_params(),
            timeout=self.timeout_seconds,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ArxivClientError("arXiv API request failed.") from exc

        return self._parse_feed(response.text)

    def _build_query_params(self) -> dict[str, str | int]:
        category_query = " OR ".join(f"cat:{category}" for category in self.categories)
        return {
            "search_query": category_query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

    def _parse_feed(self, feed_xml: str) -> list[ArxivPaper]:
        try:
            root = ElementTree.fromstring(feed_xml)
        except ElementTree.ParseError as exc:
            raise ArxivClientError("arXiv API returned invalid XML.") from exc

        papers: list[ArxivPaper] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            paper = ArxivPaper(
                title=self._required_text(entry, "title"),
                summary=self._required_text(entry, "summary"),
                published_date=self._parse_published_date(self._required_text(entry, "published")),
                arxiv_url=self._required_text(entry, "id"),
                authors=self._parse_authors(entry),
            )
            papers.append(paper)

        return papers

    def _required_text(self, entry: ElementTree.Element, tag_name: str) -> str:
        element = entry.find(f"atom:{tag_name}", ATOM_NS)
        text = element.text if element is not None else None
        cleaned_text = self._normalize_whitespace(text or "")
        if not cleaned_text:
            raise ArxivClientError(f"arXiv entry is missing required field: {tag_name}.")

        return cleaned_text

    def _parse_authors(self, entry: ElementTree.Element) -> list[str]:
        authors: list[str] = []
        for author in entry.findall("atom:author", ATOM_NS):
            name = author.find("atom:name", ATOM_NS)
            cleaned_name = self._normalize_whitespace(name.text if name is not None else "")
            if cleaned_name:
                authors.append(cleaned_name)

        return authors

    @staticmethod
    def _parse_published_date(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ArxivClientError("arXiv entry has an invalid published date.") from exc

    @staticmethod
    def _normalize_whitespace(value: str) -> str:
        return " ".join(value.split())
