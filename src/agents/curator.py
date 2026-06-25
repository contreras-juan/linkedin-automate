from __future__ import annotations

from src.state import ScoredPaperRecord, WorkflowState
from src.tools import score_papers_by_embedding
from src.tools.curator_tool import DEFAULT_FILTER_PROFILE_PATH


SYSTEM_PROMPT = """
Eres el Curator Agent. Tu responsabilidad es seleccionar papers relevantes usando
scoring semántico. Lees papers desde el estado global, invocas la tool de scoring y
devuelves una mutación con papers ordenados por relevancia.
""".strip()


def curator_node(
    state: WorkflowState,
    profile_path: str = DEFAULT_FILTER_PROFILE_PATH,
) -> WorkflowState:
    if not state.raw_papers:
        return state.with_error("Curator Agent requires raw_papers in WorkflowState.")

    scored_papers = score_papers_by_embedding.invoke(
        {
            "papers": [paper.model_dump(mode="json") for paper in state.raw_papers],
            "profile_path": profile_path,
        }
    )
    scored_records = [
        ScoredPaperRecord(
            **scored_paper,
            rationale=f"Semantic similarity score: {scored_paper['score']:.3f}.",
        )
        for scored_paper in scored_papers
    ]

    return state.model_copy(update={"scored_papers": scored_records}).with_event(
        agent="curator",
        message="Scored and filtered papers.",
        metadata={"count": len(scored_records), "profile_path": profile_path},
    )
