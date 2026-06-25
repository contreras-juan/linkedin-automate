from __future__ import annotations

from src.state import GeneratedPostRecord, WorkflowState
from src.tools import generate_linkedin_posts


SYSTEM_PROMPT = """
Eres el Writer Agent. Tu responsabilidad es convertir papers curados en publicaciones
de LinkedIn en español profesional. No consultas APIs directamente; delegas la generación
en la writer tool y devuelves posts estructurados al estado global.
""".strip()


def writer_node(state: WorkflowState) -> WorkflowState:
    if not state.scored_papers:
        return state.with_error("Writer Agent requires scored_papers in WorkflowState.")

    generated_posts = generate_linkedin_posts.invoke(
        {
            "scored_papers": [paper.model_dump(mode="json") for paper in state.scored_papers],
            "content_instructions": state.content_instructions,
        }
    )
    post_records = [GeneratedPostRecord.model_validate(post) for post in generated_posts]

    return state.model_copy(update={"generated_posts": post_records}).with_event(
        agent="writer",
        message="Generated LinkedIn posts.",
        metadata={"count": len(post_records)},
    )
