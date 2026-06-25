import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "sqlite:///apps/backend/test.db"

from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from apps.backend.app import app
from apps.backend.src.database import engine, init_db
from apps.backend.src.models import AgentLog, Generation, Post
from src.generation import LMStudioClientError
from src.state import GeneratedPostRecord, ReviewRecord, WorkflowState


def clear_db() -> None:
    init_db()
    with Session(engine) as session:
        session.exec(delete(AgentLog))
        session.exec(delete(Generation))
        session.exec(delete(Post))
        session.commit()


def test_generate_endpoint_returns_draft_from_workflow(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_MAX_RESULTS", "7")
    monkeypatch.setenv("FILTER_PROFILE_PATH", "config/filter_profile.json")

    def fake_run_workflow(
        initial_state: WorkflowState,
        max_results: int,
        profile_path: str,
    ) -> WorkflowState:
        assert initial_state.content_instructions == "Use a practical tone."
        assert initial_state.config.categories == ["cs.CV", "cs.AI"]
        assert initial_state.config.interests == ["vision language models", "agent systems"]
        assert initial_state.config.min_score == 0.12
        assert initial_state.config.max_results == 9
        assert initial_state.config.max_curated_results == 4
        assert initial_state.config.content_type == "technical_summary"
        assert initial_state.config.content_focus == "Computer vision models"
        assert max_results == 9
        assert profile_path.endswith("config/filter_profile.json")
        return WorkflowState(
            generated_posts=[
                GeneratedPostRecord(
                    source_title="Agentic Research",
                    source_url="https://arxiv.org/abs/2606.00001v1",
                    score=0.91,
                    content="Generated LinkedIn draft. #AI",
                    hashtags=["#AI"],
                )
            ],
            reviews=[
                ReviewRecord(
                    source_title="Agentic Research",
                    approved=True,
                    notes=[],
                )
            ],
        )

    monkeypatch.setattr("apps.backend.app.run_workflow", fake_run_workflow)
    monkeypatch.setattr(
        "apps.backend.app._persist_workflow_generation",
        lambda *_: (SimpleNamespace(id=1), SimpleNamespace(id=2)),
    )

    response = TestClient(app).post(
        "/api/generate",
        json={
            "instructions": "Use a practical tone.",
            "categories": ["cs.CV", "cs.AI"],
            "interests": ["vision language models", "agent systems"],
            "min_score": 0.12,
            "max_results": 9,
            "max_curated_results": 4,
            "content_type": "technical_summary",
            "content_focus": "Computer vision models",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "post_id": 1,
        "generation_id": 2,
        "draft": "Generated LinkedIn draft. #AI",
        "title": "Agentic Research",
        "score": 0.91,
        "approved": True,
        "hashtags": ["#AI"],
    }


def test_generate_endpoint_rejects_empty_instructions() -> None:
    response = TestClient(app).post("/api/generate", json={"instructions": ""})

    assert response.status_code == 422


def test_generate_endpoint_returns_502_when_workflow_has_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.backend.app.run_workflow",
        lambda **_: WorkflowState(errors=["Writer Agent failed."]),
    )

    response = TestClient(app).post(
        "/api/generate",
        json={"instructions": "Use a practical tone."},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Writer Agent failed."


def test_regenerate_endpoint_rewrites_existing_draft(monkeypatch) -> None:
    class FakeLMStudioClient:
        def generate_chat_completion(self, messages, temperature, max_tokens):
            assert temperature == 0.5
            assert max_tokens == 700
            assert "Make it more concise." in messages[1]["content"]
            assert "Original draft. #AI" in messages[1]["content"]
            return "Shorter draft with the same core idea. #AI #Agents"

    monkeypatch.setattr("apps.backend.app.LMStudioClient", FakeLMStudioClient)
    monkeypatch.setattr(
        "apps.backend.app._persist_regenerated_generation",
        lambda *_: (SimpleNamespace(id=3), SimpleNamespace(id=4)),
    )

    response = TestClient(app).post(
        "/api/regenerate",
        json={
            "draft": "Original draft. #AI",
            "instructions": "Make it more concise.",
            "title": "Agentic Research",
            "content_type": "linkedin_post",
            "content_focus": "AI agents",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "post_id": 3,
        "generation_id": 4,
        "draft": "Shorter draft with the same core idea. #AI #Agents",
        "title": "Agentic Research",
        "score": 0.0,
        "approved": True,
        "hashtags": ["#AI", "#Agents"],
    }


def test_regenerate_endpoint_returns_502_when_llm_fails(monkeypatch) -> None:
    class FailingLMStudioClient:
        def generate_chat_completion(self, messages, temperature, max_tokens):
            raise LMStudioClientError("boom")

    monkeypatch.setattr("apps.backend.app.LMStudioClient", FailingLMStudioClient)

    response = TestClient(app).post(
        "/api/regenerate",
        json={
            "draft": "Original draft.",
            "instructions": "Make it shorter.",
            "title": "Agentic Research",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Regeneration request failed."


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_posts_endpoint_returns_empty_list() -> None:
    clear_db()

    response = TestClient(app).get("/api/posts")

    assert response.status_code == 200
    assert response.json() == []


def test_post_trace_endpoint_returns_active_generation_logs() -> None:
    clear_db()
    with Session(engine) as session:
        post = Post(title="Agentic Research", source_url="https://arxiv.org/abs/1")
        session.add(post)
        session.commit()
        session.refresh(post)

        generation = Generation(
            post_id=post.id or 0,
            content="Draft",
            hashtags=["#AI"],
        )
        session.add(generation)
        session.commit()
        session.refresh(generation)

        session.add(
            AgentLog(
                generation_id=generation.id or 0,
                sequence=0,
                agent_name="researcher",
                message="Fetched papers.",
                extra={"count": 1},
            )
        )
        post.active_generation_id = generation.id
        session.add(post)
        session.commit()
        post_id = post.id

    response = TestClient(app).get(f"/api/posts/{post_id}/trace")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] > 0
    assert payload[0] | {"id": 0} == {
        "id": 0,
        "sequence": 0,
        "agent_name": "researcher",
        "message": "Fetched papers.",
        "metadata": {"count": 1},
    }
