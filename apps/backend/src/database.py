from __future__ import annotations

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from apps.backend.src import models  # noqa: F401


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/linkedin_automate"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
