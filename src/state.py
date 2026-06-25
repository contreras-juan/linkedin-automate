from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


AgentName = Literal["researcher", "curator", "writer", "reviewer"]


class PaperRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    published_date: datetime
    arxiv_url: HttpUrl
    authors: list[str] = Field(default_factory=list)


class ScoredPaperRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    paper: PaperRecord
    score: float
    rationale: str | None = None


class GeneratedPostRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_title: str = Field(min_length=1)
    source_url: HttpUrl
    score: float
    content: str = Field(min_length=1)
    hashtags: list[str] = Field(default_factory=list)


class ReviewRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_title: str = Field(min_length=1)
    approved: bool
    notes: list[str] = Field(default_factory=list)


class AgentEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent: AgentName
    message: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    categories: list[str] = Field(default_factory=lambda: ["cs.CL", "cs.AI", "cs.LG"])
    interests: list[str] = Field(
        default_factory=lambda: [
            "large language models for practical automation",
            "natural language processing applications",
            "AI agents and autonomous workflows",
            "retrieval augmented generation and semantic search",
            "machine learning systems useful for content generation",
        ]
    )
    min_score: float = Field(default=0.25, ge=-1.0, le=1.0)
    max_results: int = Field(default=3, ge=1, le=50)
    max_curated_results: int = Field(default=5, ge=1, le=20)
    content_type: str = Field(default="linkedin_post", min_length=1)
    content_focus: str | None = None


class WorkflowState(BaseModel):
    model_config = ConfigDict(frozen=True)

    content_instructions: str | None = None
    config: WorkflowConfig = Field(default_factory=WorkflowConfig)
    raw_papers: list[PaperRecord] = Field(default_factory=list)
    scored_papers: list[ScoredPaperRecord] = Field(default_factory=list)
    generated_posts: list[GeneratedPostRecord] = Field(default_factory=list)
    reviews: list[ReviewRecord] = Field(default_factory=list)
    events: list[AgentEvent] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def with_event(
        self,
        agent: AgentName,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> "WorkflowState":
        return self.model_copy(
            update={
                "events": [
                    *self.events,
                    AgentEvent(agent=agent, message=message, metadata=metadata or {}),
                ]
            }
        )

    def with_error(self, error: str) -> "WorkflowState":
        return self.model_copy(update={"errors": [*self.errors, error]})
