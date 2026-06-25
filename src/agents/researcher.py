from __future__ import annotations

from typing import Sequence

from src.state import PaperRecord, WorkflowState
from src.tools import search_recent_arxiv_papers
from src.tools.arxiv_tool import DEFAULT_RESEARCH_CATEGORIES


SYSTEM_PROMPT = """
Eres el Researcher Agent. Tu responsabilidad es recuperar papers recientes de arXiv
usando exclusivamente las tools disponibles. No filtras, no escribes posts y no revisas
contenido; solo devuelves papers normalizados al estado global.
""".strip()


def researcher_node(
    state: WorkflowState,
    categories: Sequence[str] = DEFAULT_RESEARCH_CATEGORIES,
    max_results: int = 10,
) -> WorkflowState:
    raw_papers = search_recent_arxiv_papers.invoke(
        {"categories": list(categories), "max_results": max_results}
    )
    paper_records = [PaperRecord.model_validate(paper) for paper in raw_papers]

    return state.model_copy(update={"raw_papers": paper_records}).with_event(
        agent="researcher",
        message="Fetched recent arXiv papers.",
        metadata={"count": len(paper_records), "categories": list(categories)},
    )
