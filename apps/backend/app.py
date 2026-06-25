from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Session, select


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.graph import run_workflow  # noqa: E402
from src.generation import LLMClientError, create_llm_client  # noqa: E402
from src.state import WorkflowConfig, WorkflowState  # noqa: E402
from apps.backend.src.database import engine, init_db  # noqa: E402
from apps.backend.src.models import AgentLog, Generation, Post, utc_now  # noqa: E402


class GenerateRequest(BaseModel):
    instructions: str = Field(min_length=1)
    categories: list[str] | None = None
    interests: list[str] | None = None
    min_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    max_results: int | None = Field(default=None, ge=1, le=50)
    max_curated_results: int | None = Field(default=None, ge=1, le=20)
    content_type: str | None = None
    content_focus: str | None = None


class GenerateResponse(BaseModel):
    post_id: int | None = None
    generation_id: int | None = None
    draft: str
    title: str
    score: float
    approved: bool
    hashtags: list[str]


class RegenerateRequest(BaseModel):
    draft: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    title: str = Field(default="Current LinkedIn draft", min_length=1)
    content_type: str = Field(default="linkedin_post", min_length=1)
    content_focus: str | None = None
    post_id: int | None = None


class PostListItem(BaseModel):
    id: int
    title: str
    source_url: str
    publishing_status: str
    active_generation_id: int | None
    content: str | None
    score: float | None
    approved: bool | None
    hashtags: list[str]


class AgentLogRead(BaseModel):
    id: int
    sequence: int
    agent_name: str
    message: str
    metadata: dict[str, Any]


def _get_csv_env(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


def _resolve_project_path_env(name: str, default: str) -> str:
    raw_value = os.getenv(name, default)
    path = Path(raw_value)
    if path.is_absolute():
        return str(path)

    return str(PROJECT_ROOT / path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="LinkedIn AI Automator API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_csv_env(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/posts", response_model=list[PostListItem])
def list_posts() -> list[PostListItem]:
    with Session(engine) as session:
        posts = session.exec(select(Post).order_by(Post.updated_at.desc())).all()
        return [_to_post_list_item(session, post) for post in posts]


@app.get("/api/posts/{post_id}/trace", response_model=list[AgentLogRead])
def get_post_trace(post_id: int) -> list[AgentLogRead]:
    with Session(engine) as session:
        post = session.get(Post, post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="Post not found.")
        if post.active_generation_id is None:
            return []

        logs = session.exec(
            select(AgentLog)
            .where(AgentLog.generation_id == post.active_generation_id)
            .order_by(AgentLog.sequence)
        ).all()
        return [
            AgentLogRead(
                id=log.id or 0,
                sequence=log.sequence,
                agent_name=log.agent_name,
                message=log.message,
                metadata=log.extra,
            )
            for log in logs
        ]


@app.post("/api/generate", response_model=GenerateResponse)
def generate_post(payload: GenerateRequest) -> GenerateResponse:
    workflow_config = _build_workflow_config(payload)
    try:
        final_state = run_workflow(
            initial_state=WorkflowState(
                content_instructions=payload.instructions,
                config=workflow_config,
            ),
            max_results=workflow_config.max_results,
            profile_path=_resolve_project_path_env(
                "FILTER_PROFILE_PATH",
                "config/filter_profile.json",
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Workflow execution failed.") from exc

    if final_state.errors:
        raise HTTPException(status_code=502, detail=final_state.errors[-1])
    if not final_state.generated_posts:
        raise HTTPException(status_code=502, detail="Workflow did not generate a post.")

    post = final_state.generated_posts[0]
    review = final_state.reviews[0] if final_state.reviews else None
    db_post, generation = _persist_workflow_generation(final_state, payload, workflow_config)
    return GenerateResponse(
        post_id=db_post.id,
        generation_id=generation.id,
        draft=post.content,
        title=post.source_title,
        score=post.score,
        approved=review.approved if review else False,
        hashtags=post.hashtags,
    )


@app.post("/api/regenerate", response_model=GenerateResponse)
def regenerate_post(payload: RegenerateRequest) -> GenerateResponse:
    try:
        draft = create_llm_client().generate_chat_completion(
            messages=_build_regeneration_messages(payload),
            temperature=0.5,
            max_tokens=700,
        )
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail="Regeneration request failed.") from exc

    db_post, generation = _persist_regenerated_generation(payload, draft)
    return GenerateResponse(
        post_id=db_post.id,
        generation_id=generation.id,
        draft=draft,
        title=payload.title,
        score=0.0,
        approved=True,
        hashtags=_extract_hashtags(draft),
    )


def _build_workflow_config(payload: GenerateRequest) -> WorkflowConfig:
    default_config = WorkflowConfig(max_results=_get_int_env("WORKFLOW_MAX_RESULTS", 3))
    return default_config.model_copy(
        update={
            "categories": payload.categories or default_config.categories,
            "interests": payload.interests or default_config.interests,
            "min_score": payload.min_score
            if payload.min_score is not None
            else default_config.min_score,
            "max_results": payload.max_results or default_config.max_results,
            "max_curated_results": payload.max_curated_results
            or default_config.max_curated_results,
            "content_type": payload.content_type or default_config.content_type,
            "content_focus": payload.content_focus or default_config.content_focus,
        }
    )


def _persist_workflow_generation(
    final_state: WorkflowState,
    payload: GenerateRequest,
    workflow_config: WorkflowConfig,
) -> tuple[Post, Generation]:
    generated_post = final_state.generated_posts[0]
    review = final_state.reviews[0] if final_state.reviews else None
    scored_paper = next(
        (
            scored_paper
            for scored_paper in final_state.scored_papers
            if scored_paper.paper.title == generated_post.source_title
        ),
        None,
    )
    paper_data = (
        scored_paper.paper.model_dump(mode="json")
        if scored_paper is not None
        else {"title": generated_post.source_title, "source_url": str(generated_post.source_url)}
    )

    with Session(engine) as session:
        post = _get_or_create_post(
            session=session,
            title=generated_post.source_title,
            source_url=str(generated_post.source_url),
            paper_data=paper_data,
        )
        generation = Generation(
            post_id=post.id or 0,
            content=generated_post.content,
            content_type=workflow_config.content_type,
            content_focus=workflow_config.content_focus,
            score=generated_post.score,
            approved=review.approved if review else False,
            hashtags=generated_post.hashtags,
            paper_data=paper_data,
            config=workflow_config.model_dump(mode="json"),
            prompt_data={"instructions": payload.instructions},
        )
        session.add(generation)
        session.commit()
        session.refresh(generation)

        for index, event in enumerate(final_state.events):
            session.add(
                AgentLog(
                    generation_id=generation.id or 0,
                    sequence=index,
                    agent_name=event.agent,
                    message=event.message,
                    extra=event.metadata,
                    created_at=event.created_at,
                )
            )

        post.active_generation_id = generation.id
        post.publishing_status = "draft"
        post.updated_at = utc_now()
        session.add(post)
        session.commit()
        session.refresh(post)
        session.refresh(generation)
        return post, generation


def _persist_regenerated_generation(
    payload: RegenerateRequest,
    draft: str,
) -> tuple[Post, Generation]:
    with Session(engine) as session:
        post = session.get(Post, payload.post_id) if payload.post_id is not None else None
        if post is None:
            post = _get_or_create_post(
                session=session,
                title=payload.title,
                source_url="",
                paper_data={"title": payload.title},
            )

        generation = Generation(
            post_id=post.id or 0,
            content=draft,
            content_type=payload.content_type,
            content_focus=payload.content_focus,
            score=0.0,
            approved=True,
            hashtags=_extract_hashtags(draft),
            paper_data=post.paper_data,
            prompt_data={
                "regeneration_instructions": payload.instructions,
                "previous_draft": payload.draft,
            },
        )
        session.add(generation)
        session.commit()
        session.refresh(generation)

        session.add(
            AgentLog(
                generation_id=generation.id or 0,
                sequence=0,
                agent_name="writer",
                message="Regenerated existing LinkedIn draft.",
                extra={"instructions": payload.instructions},
            )
        )
        post.active_generation_id = generation.id
        post.updated_at = utc_now()
        session.add(post)
        session.commit()
        session.refresh(post)
        session.refresh(generation)
        return post, generation


def _get_or_create_post(
    session: Session,
    title: str,
    source_url: str,
    paper_data: dict[str, Any],
) -> Post:
    post = None
    if source_url:
        post = session.exec(select(Post).where(Post.source_url == source_url)).first()
    if post is None:
        post = Post(title=title, source_url=source_url, paper_data=paper_data)
    else:
        post.title = title
        post.paper_data = paper_data

    post.updated_at = utc_now()
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


def _to_post_list_item(session: Session, post: Post) -> PostListItem:
    generation = (
        session.get(Generation, post.active_generation_id)
        if post.active_generation_id is not None
        else None
    )
    return PostListItem(
        id=post.id or 0,
        title=post.title,
        source_url=post.source_url,
        publishing_status=post.publishing_status,
        active_generation_id=post.active_generation_id,
        content=generation.content if generation else None,
        score=generation.score if generation else None,
        approved=generation.approved if generation else None,
        hashtags=generation.hashtags if generation else [],
    )


def _build_regeneration_messages(payload: RegenerateRequest) -> list[dict[str, str]]:
    focus = f"\nFoco del contenido: {payload.content_focus}" if payload.content_focus else ""
    return [
        {
            "role": "system",
            "content": (
                "Eres un editor técnico para LinkedIn. Reescribes drafts manteniendo "
                "fidelidad al contenido original, claridad y un tono profesional."
            ),
        },
        {
            "role": "user",
            "content": f"""
Reescribe el siguiente draft de LinkedIn aplicando la instrucción del usuario.

Instrucción de regeneración:
{payload.instructions}

Tipo de contenido: {payload.content_type}{focus}

Reglas:
- Conserva el significado central del draft original.
- No inventes resultados, cifras ni claims nuevos.
- Mantén o ajusta hashtags si la instrucción lo requiere.
- Devuelve solo el nuevo texto final, sin explicación adicional.

Draft actual:
{payload.draft}
""".strip(),
        },
    ]


def _extract_hashtags(content: str) -> list[str]:
    hashtags: list[str] = []
    seen: set[str] = set()
    for token in content.split():
        if not token.startswith("#"):
            continue
        hashtag = token.strip(".,;:!?)(")
        normalized = hashtag.lower()
        if normalized not in seen:
            hashtags.append(hashtag)
            seen.add(normalized)

    return hashtags
