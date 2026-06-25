from __future__ import annotations

from datetime import datetime, timezone

from src.agents.curator import curator_node
from src.agents.researcher import researcher_node
from src.agents.reviewer import reviewer_node
from src.agents.writer import writer_node
from src.state import GeneratedPostRecord, PaperRecord, ScoredPaperRecord, WorkflowConfig, WorkflowState


class FakeTool:
    def __init__(self, result: object) -> None:
        self.result = result
        self.payload: dict[str, object] | None = None

    def invoke(self, payload: dict[str, object]) -> object:
        self.payload = payload
        return self.result


def test_researcher_node_fetches_papers_through_arxiv_tool(monkeypatch) -> None:
    fake_tool = FakeTool([_paper_payload()])
    monkeypatch.setattr("src.agents.researcher.search_recent_arxiv_papers", fake_tool)

    next_state = researcher_node(WorkflowState(), categories=("cs.AI",), max_results=1)

    assert fake_tool.payload == {"categories": ["cs.AI"], "max_results": 1}
    assert [paper.title for paper in next_state.raw_papers] == ["Agentic Research"]
    assert next_state.events[-1].agent == "researcher"
    assert next_state.events[-1].metadata["count"] == 1


def test_curator_node_scores_raw_papers_through_tool(monkeypatch) -> None:
    fake_tool = FakeTool([{"paper": _paper_payload(), "score": 0.91}])
    monkeypatch.setattr("src.agents.curator.score_papers_by_embedding", fake_tool)
    state = WorkflowState(
        raw_papers=[PaperRecord.model_validate(_paper_payload())],
        config=WorkflowConfig(
            interests=["computer vision foundation models"],
            min_score=0.12,
            max_curated_results=2,
        ),
    )

    next_state = curator_node(state, profile_path="config/filter_profile.json")

    assert fake_tool.payload is not None
    assert fake_tool.payload["profile_path"] == "config/filter_profile.json"
    assert fake_tool.payload["profile"] == {
        "name": "dynamic_workflow_profile",
        "interests": ["computer vision foundation models"],
        "min_score": 0.12,
        "max_results": 2,
    }
    assert next_state.scored_papers[0].score == 0.91
    assert next_state.scored_papers[0].rationale == "Semantic similarity score: 0.910."
    assert next_state.events[-1].agent == "curator"


def test_curator_node_requires_raw_papers() -> None:
    next_state = curator_node(WorkflowState())

    assert next_state.errors == ["Curator Agent requires raw_papers in WorkflowState."]


def test_writer_node_generates_posts_through_tool(monkeypatch) -> None:
    fake_tool = FakeTool([_post_payload()])
    monkeypatch.setattr("src.agents.writer.generate_linkedin_posts", fake_tool)
    state = WorkflowState(
        scored_papers=[_scored_paper_record()],
        content_instructions="Use an executive tone.",
        config=WorkflowConfig(
            content_type="technical_summary",
            content_focus="Only LLM systems.",
        ),
    )

    next_state = writer_node(state)

    assert fake_tool.payload is not None
    assert fake_tool.payload["content_instructions"] == (
        "Tipo de contenido: technical_summary.\n"
        "Enfoque temático: Only LLM systems.\n"
        "Use an executive tone."
    )
    assert next_state.generated_posts[0].source_title == "Agentic Research"
    assert next_state.generated_posts[0].hashtags == ["#AI", "#Agents"]
    assert next_state.events[-1].agent == "writer"


def test_writer_node_requires_scored_papers() -> None:
    next_state = writer_node(WorkflowState())

    assert next_state.errors == ["Writer Agent requires scored_papers in WorkflowState."]


def test_reviewer_node_reviews_generated_posts_through_tool(monkeypatch) -> None:
    fake_tool = FakeTool(
        [{"source_title": "Agentic Research", "approved": True, "notes": []}]
    )
    monkeypatch.setattr("src.agents.reviewer.review_linkedin_posts", fake_tool)
    state = WorkflowState(generated_posts=[GeneratedPostRecord.model_validate(_post_payload())])

    next_state = reviewer_node(state)

    assert fake_tool.payload is not None
    assert next_state.reviews[0].approved is True
    assert next_state.events[-1].agent == "reviewer"
    assert next_state.events[-1].metadata == {"approved": 1, "rejected": 0}


def test_reviewer_node_requires_generated_posts() -> None:
    next_state = reviewer_node(WorkflowState())

    assert next_state.errors == ["Reviewer Agent requires generated_posts in WorkflowState."]


def _paper_payload() -> dict[str, object]:
    return {
        "title": "Agentic Research",
        "summary": "A paper about multi-agent research automation.",
        "published_date": datetime(2026, 6, 25, tzinfo=timezone.utc).isoformat(),
        "arxiv_url": "https://arxiv.org/abs/2606.00001v1",
        "authors": ["Ada Lovelace"],
    }


def _scored_paper_record() -> ScoredPaperRecord:
    return ScoredPaperRecord(
        paper=PaperRecord.model_validate(_paper_payload()),
        score=0.91,
        rationale="Semantic similarity score: 0.910.",
    )


def _post_payload() -> dict[str, object]:
    return {
        "source_title": "Agentic Research",
        "source_url": "https://arxiv.org/abs/2606.00001v1",
        "score": 0.91,
        "content": "Agentic Research helps automate research workflows. #AI #Agents",
        "hashtags": ["#AI", "#Agents"],
    }
