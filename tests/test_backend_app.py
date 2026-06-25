from fastapi.testclient import TestClient

from apps.backend.app import app
from src.state import GeneratedPostRecord, ReviewRecord, WorkflowState


def test_generate_endpoint_returns_draft_from_workflow(monkeypatch) -> None:
    def fake_run_workflow(initial_state: WorkflowState, max_results: int) -> WorkflowState:
        assert initial_state.content_instructions == "Use a practical tone."
        assert max_results == 3
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

    response = TestClient(app).post(
        "/api/generate",
        json={"instructions": "Use a practical tone."},
    )

    assert response.status_code == 200
    assert response.json() == {
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


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
