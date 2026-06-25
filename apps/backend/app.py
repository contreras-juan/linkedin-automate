from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.graph import run_workflow  # noqa: E402
from src.state import WorkflowState  # noqa: E402


class GenerateRequest(BaseModel):
    instructions: str = Field(min_length=1)


class GenerateResponse(BaseModel):
    draft: str
    title: str
    score: float
    approved: bool
    hashtags: list[str]


app = FastAPI(title="LinkedIn AI Automator API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/generate", response_model=GenerateResponse)
def generate_post(payload: GenerateRequest) -> GenerateResponse:
    try:
        final_state = run_workflow(
            initial_state=WorkflowState(content_instructions=payload.instructions),
            max_results=3,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Workflow execution failed.") from exc

    if final_state.errors:
        raise HTTPException(status_code=502, detail=final_state.errors[-1])
    if not final_state.generated_posts:
        raise HTTPException(status_code=502, detail="Workflow did not generate a post.")

    post = final_state.generated_posts[0]
    review = final_state.reviews[0] if final_state.reviews else None
    return GenerateResponse(
        draft=post.content,
        title=post.source_title,
        score=post.score,
        approved=review.approved if review else False,
        hashtags=post.hashtags,
    )
