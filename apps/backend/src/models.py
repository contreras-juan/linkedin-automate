from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    source_url: str = Field(default="", index=True)
    publishing_status: str = Field(default="draft", index=True)
    active_generation_id: int | None = Field(default=None, index=True)
    paper_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    generations: list["Generation"] = Relationship(back_populates="post")


class Generation(SQLModel, table=True):
    __tablename__ = "generations"

    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id", index=True)
    content: str
    content_type: str = Field(default="linkedin_post", index=True)
    content_focus: str | None = None
    score: float = Field(default=0.0)
    approved: bool = Field(default=False)
    hashtags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    paper_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    prompt_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)

    post: Post = Relationship(back_populates="generations")
    agent_logs: list["AgentLog"] = Relationship(back_populates="generation")


class AgentLog(SQLModel, table=True):
    __tablename__ = "agent_logs"

    id: int | None = Field(default=None, primary_key=True)
    generation_id: int = Field(foreign_key="generations.id", index=True)
    sequence: int = Field(index=True)
    agent_name: str = Field(index=True)
    message: str
    extra: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utc_now)

    generation: Generation = Relationship(back_populates="agent_logs")
