from __future__ import annotations

from src.state import ReviewRecord, WorkflowState
from src.tools import review_linkedin_posts


SYSTEM_PROMPT = """
Eres el Reviewer Agent. Tu responsabilidad es revisar publicaciones generadas y detectar
riesgos básicos de alucinación, claims absolutos o falta de trazabilidad al paper fuente.
No reescribes contenido; devuelves revisiones estructuradas.
""".strip()


def reviewer_node(state: WorkflowState) -> WorkflowState:
    if not state.generated_posts:
        return state.with_error("Reviewer Agent requires generated_posts in WorkflowState.")

    reviews = review_linkedin_posts.invoke(
        {"posts": [post.model_dump(mode="json") for post in state.generated_posts]}
    )
    review_records = [ReviewRecord.model_validate(review) for review in reviews]
    approved_count = sum(1 for review in review_records if review.approved)

    return state.model_copy(update={"reviews": review_records}).with_event(
        agent="reviewer",
        message="Reviewed generated LinkedIn posts.",
        metadata={
            "approved": approved_count,
            "rejected": len(review_records) - approved_count,
        },
    )
