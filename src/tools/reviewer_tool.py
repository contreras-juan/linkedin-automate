from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.state import GeneratedPostRecord


RISKY_CLAIMS = (
    "garantiza",
    "revoluciona por completo",
    "sin errores",
    "100%",
    "definitivo",
)


@tool
def review_linkedin_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Review generated LinkedIn posts for basic grounding and hallucination risks."""

    reviews: list[dict[str, Any]] = []
    for raw_post in posts:
        post = GeneratedPostRecord.model_validate(raw_post)
        notes = _review_post(post)
        reviews.append(
            {
                "source_title": post.source_title,
                "approved": not notes,
                "notes": notes,
            }
        )

    return reviews


def _review_post(post: GeneratedPostRecord) -> list[str]:
    notes: list[str] = []
    content_lower = post.content.lower()
    title_terms = {
        term.strip(".,:;()[]").lower()
        for term in post.source_title.split()
        if len(term.strip(".,:;()[]")) > 4
    }

    if not post.content.strip():
        notes.append("Post content is empty.")
    if not post.hashtags:
        notes.append("Post does not include extracted hashtags.")
    if title_terms and not any(term in content_lower for term in title_terms):
        notes.append("Post does not mention recognizable terms from the source title.")

    risky_matches = [claim for claim in RISKY_CLAIMS if claim in content_lower]
    if risky_matches:
        notes.append(f"Post contains risky absolute claims: {', '.join(risky_matches)}.")

    return notes
